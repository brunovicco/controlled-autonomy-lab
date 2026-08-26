"""Command-line interface for the controlled-autonomy demonstration."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from autonomy_lab.adapters.benchmark_artifacts import (
    assert_benchmark_output_available,
    write_benchmark_artifacts,
)
from autonomy_lab.adapters.benchmark_metadata import benchmark_environment_from_env
from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.providers import client_from_env
from autonomy_lab.adapters.run_log import MetadataRunRecorder
from autonomy_lab.application.benchmark import run_benchmark, summarize_benchmark
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.comparison import (
    PatternRunner,
    repeat_pattern,
    summarize_repetitions,
)
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.application.model_ports import ModelClient
from autonomy_lab.application.patterns.agent import BoundedIncidentAgent
from autonomy_lab.application.patterns.augmented import AugmentedIncidentAnalysis
from autonomy_lab.application.patterns.chaining import ChainedIncidentAnalysis
from autonomy_lab.application.patterns.evaluator_optimizer import (
    EvaluatorOptimizerIncidentAnalysis,
)
from autonomy_lab.application.patterns.parallel import ParallelIncidentAnalysis
from autonomy_lab.application.patterns.routing import RoutedIncidentAnalysis
from autonomy_lab.domain.autonomy import AutonomyPattern, PatternRun
from autonomy_lab.domain.benchmark import BenchmarkConfig, BenchmarkStatus
from autonomy_lab.domain.claim_evaluation import ClaimEvaluationReport
from autonomy_lab.domain.grounding import GroundingFinding, GroundingReport


def _build_runner(
    pattern: AutonomyPattern,
    *,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> PatternRunner:
    if pattern is AutonomyPattern.AUGMENTED:
        return AugmentedIncidentAnalysis(store=store, model=model)
    if pattern is AutonomyPattern.CHAINING:
        return ChainedIncidentAnalysis(store=store, model=model)
    if pattern is AutonomyPattern.ROUTING:
        return RoutedIncidentAnalysis(store=store, model=model)
    if pattern is AutonomyPattern.PARALLEL:
        return ParallelIncidentAnalysis(store=store, model=model)
    if pattern is AutonomyPattern.EVALUATOR_OPTIMIZER:
        return EvaluatorOptimizerIncidentAnalysis(store=store, model=model)
    return BoundedIncidentAgent(store=store, model=model)


def _client_from_env() -> ModelClient:
    return client_from_env()


def _findings_payload(
    findings: tuple[GroundingFinding, ...],
) -> list[dict[str, object]]:
    return [
        {
            "kind": finding.kind.value,
            "value": finding.value,
            "context": finding.context,
        }
        for finding in findings
    ]


def _grounding_payload(report: GroundingReport) -> dict[str, object]:
    return {
        "supported_specifics": list(report.supported_specifics),
        "unsupported_specifics": _findings_payload(report.unsupported_specifics),
        "proposed_specifics": _findings_payload(report.proposed_specifics),
        "causality_overclaims": _findings_payload(report.causality_overclaims),
        "uncertainty_preserved": report.uncertainty_preserved,
        "specific_grounding_ratio": round(report.specific_grounding_ratio, 4),
    }


def _claim_evaluation_payload(report: ClaimEvaluationReport) -> dict[str, object]:
    return {
        "claims": [
            {
                "claim": claim.claim,
                "kind": claim.kind.value,
                "rationale": claim.rationale,
                "evidence_sources": list(claim.evidence_sources),
            }
            for claim in report.claims
        ],
        "supported_facts": report.supported_fact_count,
        "supported_inferences": report.supported_inference_count,
        "proposed_actions": report.proposed_action_count,
        "unsupported_claims": report.unsupported_claim_count,
        "evaluable_claims": report.evaluable_claim_count,
        "support_ratio": round(report.support_ratio, 4),
    }


def _run_payload(
    run: PatternRun,
    grounding: GroundingReport | None = None,
    claim_evaluation: ClaimEvaluationReport | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "pattern": run.pattern.value,
        "incident_id": run.incident_id,
        "answer": run.answer,
        "model_calls": run.model_calls,
        "tool_calls": run.tool_calls,
        "steps": list(run.steps),
        "input_tokens": run.usage.input_tokens,
        "output_tokens": run.usage.output_tokens,
        "latency_ms": round(run.latency_ms, 3),
    }
    if grounding is not None:
        payload["grounding"] = _grounding_payload(grounding)
    if claim_evaluation is not None:
        payload["claim_evaluation"] = _claim_evaluation_payload(claim_evaluation)
    return payload


def _run_failure_payload(
    *,
    pattern: AutonomyPattern,
    incident_id: str,
    status: str,
    error: ModelProviderError,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "pattern": pattern.value,
        "incident_id": incident_id,
        "status": status,
        "error": str(error),
    }
    if isinstance(error, ModelRateLimitError) and error.retry_after is not None:
        payload["retry_after"] = error.retry_after
    return payload


def _print_run_failure(
    *,
    pattern: AutonomyPattern,
    incident_id: str,
    status: str,
    error: ModelProviderError,
    as_json: bool,
) -> int:
    payload = _run_failure_payload(
        pattern=pattern,
        incident_id=incident_id,
        status=status,
        error=error,
    )
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"pattern: {pattern.value}", file=sys.stderr)
        print(f"status:  {status}", file=sys.stderr)
        print(f"error:   {error}", file=sys.stderr)
        retry_after = payload.get("retry_after")
        if retry_after is not None:
            print(f"retry after: {retry_after}", file=sys.stderr)
    return 2


def _print_grounding(report: GroundingReport) -> None:
    print("\ngrounding:\n")
    print(f"supported specifics:   {len(report.supported_specifics)}")
    print(f"unsupported specifics: {report.unsupported_count}")
    print(f"proposed parameters:   {report.proposed_count}")
    print(f"causality overclaims:  {report.causality_overclaim_count}")
    print(f"uncertainty preserved: {'yes' if report.uncertainty_preserved else 'no'}")
    print(f"specific grounding:    {report.specific_grounding_ratio:.1%}")
    for finding in (
        *report.unsupported_specifics,
        *report.proposed_specifics,
        *report.causality_overclaims,
    ):
        print(f"- {finding.kind.value}: {finding.value!r} :: {finding.context}")


def _print_claim_evaluation(report: ClaimEvaluationReport) -> None:
    print("\nclaim evaluation v2:\n")
    print(f"supported facts:       {report.supported_fact_count}")
    print(f"supported inferences:  {report.supported_inference_count}")
    print(f"proposed actions:      {report.proposed_action_count}")
    print(f"unsupported claims:    {report.unsupported_claim_count}")
    print(f"evaluable claims:      {report.evaluable_claim_count}")
    print(f"claim support:         {report.support_ratio:.1%}")
    for claim in report.claims:
        sources = ",".join(claim.evidence_sources) or "-"
        print(f"- {claim.kind.value}: {claim.claim!r} [{claim.rationale}; sources={sources}]")


def _print_run(
    run: PatternRun,
    *,
    as_json: bool,
    grounding: GroundingReport | None = None,
    claim_evaluation: ClaimEvaluationReport | None = None,
) -> None:
    if as_json:
        print(json.dumps(_run_payload(run, grounding, claim_evaluation), indent=2))
        return
    print(f"pattern:       {run.pattern.value}")
    print(f"model calls:   {run.model_calls}")
    print(f"tool calls:    {run.tool_calls}")
    print(f"input tokens:  {run.usage.input_tokens}")
    print(f"output tokens: {run.usage.output_tokens}")
    print(f"latency:       {run.latency_ms:.1f} ms")
    print(f"trajectory:    {' -> '.join(run.steps)}")
    print("\nanswer:\n")
    print(run.answer)
    if grounding is not None:
        _print_grounding(grounding)
    if claim_evaluation is not None:
        _print_claim_evaluation(claim_evaluation)


def _record_if_requested(run: PatternRun, trace_file: str | None) -> None:
    if trace_file:
        MetadataRunRecorder(Path(trace_file)).append(run)


def _grounding_for_run(
    run: PatternRun,
    *,
    store: InMemoryIncidentStore,
    evaluator: DeterministicGroundingEvaluator,
) -> GroundingReport:
    incident = store.get_incident(run.incident_id)
    evidence = store.get_evidence(incident)
    return evaluator.evaluate(answer=run.answer, incident=incident, evidence=evidence)


def _claim_evaluation_for_run(
    run: PatternRun,
    *,
    store: InMemoryIncidentStore,
    evaluator: DeterministicClaimEvaluatorV2,
) -> ClaimEvaluationReport:
    incident = store.get_incident(run.incident_id)
    evidence = store.get_evidence(incident)
    return evaluator.evaluate(answer=run.answer, incident=incident, evidence=evidence)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be zero or positive") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or positive")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="controlled-autonomy-lab",
        description="Run the same incident through increasing levels of LLM autonomy.",
    )
    parser.add_argument("--trace-file", help="optional metadata-only JSONL execution log")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="execute one architecture pattern")
    run_parser.add_argument("pattern", choices=[pattern.value for pattern in AutonomyPattern])
    run_parser.add_argument("--incident", default="INC-001")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument(
        "--grounding",
        action="store_true",
        help="evaluate exact specifics and causal language against the incident fixture",
    )
    run_parser.add_argument(
        "--claims",
        action="store_true",
        help="classify answer claims with the conservative deterministic v2 baseline",
    )

    compare_parser = subparsers.add_parser("compare", help="execute every pattern once")
    compare_parser.add_argument("--incident", default="INC-001")

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="run repeated architecture cycles and persist reproducible metadata-only results",
    )
    benchmark_parser.add_argument("--incident", default="INC-001")
    benchmark_parser.add_argument("--runs", type=_positive_int, default=5)
    benchmark_parser.add_argument("--output", default="results")
    benchmark_parser.add_argument(
        "--run-interval-seconds",
        type=_non_negative_float,
        default=0.0,
        help="pause between benchmark attempts without changing calls inside a pattern",
    )
    benchmark_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace runs.jsonl, summary.csv and summary.md when they already exist",
    )

    repeat_parser = subparsers.add_parser("repeat", help="measure trajectory variance")
    repeat_parser.add_argument("pattern", choices=[pattern.value for pattern in AutonomyPattern])
    repeat_parser.add_argument("--incident", default="INC-001")
    repeat_parser.add_argument("--runs", type=_positive_int, default=5)
    return parser


def _print_compare_failure(pattern: AutonomyPattern, status: str) -> None:
    print(f"{pattern.value} | - | - | - | - | - | - | - | - | - | {status}")


def _run_reproducible_benchmark(
    *,
    args: argparse.Namespace,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> int:
    output_dir = Path(args.output)
    try:
        assert_benchmark_output_available(output_dir, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    environment = benchmark_environment_from_env()
    config = BenchmarkConfig(
        incident_id=args.incident,
        runs=args.runs,
        provider=environment.provider,
        model=environment.model,
        max_tokens=environment.max_tokens,
        timeout_seconds=environment.timeout_seconds,
        reasoning_effort=environment.reasoning_effort,
        run_interval_seconds=args.run_interval_seconds,
        git_commit=environment.git_commit,
    )
    evaluator = DeterministicGroundingEvaluator()
    patterns = tuple(AutonomyPattern)

    def execute(pattern: AutonomyPattern) -> PatternRun:
        return _build_runner(pattern, store=store, model=model).run(args.incident)

    def evaluate(run: PatternRun) -> GroundingReport:
        return _grounding_for_run(run, store=store, evaluator=evaluator)

    records = run_benchmark(
        config=config,
        patterns=patterns,
        run_pattern=execute,
        evaluate_run=evaluate,
        on_success=lambda run: _record_if_requested(run, args.trace_file),
    )
    summaries = summarize_benchmark(records, patterns=patterns)
    artifacts = write_benchmark_artifacts(
        output_dir=output_dir,
        config=config,
        records=records,
        summaries=summaries,
        overwrite=args.overwrite,
    )
    partial = any(record.status is not BenchmarkStatus.OK for record in records)

    print(f"benchmark: {'partial' if partial else 'complete'}")
    print(f"provider:  {config.provider}")
    print(f"model:     {config.model}")
    print(f"commit:    {config.git_commit}")
    print(f"runs:      {config.runs} per pattern")
    print(f"jsonl:     {artifacts.runs_jsonl}")
    print(f"csv:       {artifacts.summary_csv}")
    print(f"markdown:  {artifacts.summary_markdown}")
    print("\npattern | success | rate_limited | p50_ms | grounding | trajectories")
    print("-" * 78)
    for summary in summaries:
        latency = "-" if summary.p50_latency_ms is None else f"{summary.p50_latency_ms:.1f}"
        grounding = (
            "-" if summary.mean_grounding_ratio is None else f"{summary.mean_grounding_ratio:.1%}"
        )
        print(
            f"{summary.pattern.value} | {summary.completed}/{summary.attempted} | "
            f"{summary.rate_limited} | {latency} | {grounding} | "
            f"{summary.unique_trajectories}"
        )
    return 2 if partial else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process exit code."""
    args = _parser().parse_args(argv)
    store = InMemoryIncidentStore()
    model = _client_from_env()

    if args.command == "run":
        pattern = AutonomyPattern(args.pattern)
        try:
            run = _build_runner(pattern, store=store, model=model).run(args.incident)
        except ModelRateLimitError as exc:
            return _print_run_failure(
                pattern=pattern,
                incident_id=args.incident,
                status="rate_limited",
                error=exc,
                as_json=args.json,
            )
        except ModelProviderError as exc:
            return _print_run_failure(
                pattern=pattern,
                incident_id=args.incident,
                status="provider_error",
                error=exc,
                as_json=args.json,
            )
        _record_if_requested(run, args.trace_file)
        grounding = None
        claim_evaluation = None
        if args.grounding:
            grounding = _grounding_for_run(
                run,
                store=store,
                evaluator=DeterministicGroundingEvaluator(),
            )
        if args.claims:
            claim_evaluation = _claim_evaluation_for_run(
                run,
                store=store,
                evaluator=DeterministicClaimEvaluatorV2(),
            )
        _print_run(
            run,
            as_json=args.json,
            grounding=grounding,
            claim_evaluation=claim_evaluation,
        )
        return 0

    if args.command == "compare":
        evaluator = DeterministicGroundingEvaluator()
        had_provider_errors = False
        print(
            "pattern | model_calls | tool_calls | input_tokens | output_tokens | latency_ms | "
            "unsupported | proposed | causality | uncertainty | status"
        )
        print("-" * 145)
        for pattern in AutonomyPattern:
            try:
                run = _build_runner(pattern, store=store, model=model).run(args.incident)
            except ModelRateLimitError:
                had_provider_errors = True
                _print_compare_failure(pattern, "rate_limited")
                continue
            except ModelProviderError:
                had_provider_errors = True
                _print_compare_failure(pattern, "provider_error")
                continue
            _record_if_requested(run, args.trace_file)
            grounding = _grounding_for_run(run, store=store, evaluator=evaluator)
            uncertainty = "yes" if grounding.uncertainty_preserved else "no"
            print(
                f"{pattern.value} | {run.model_calls} | {run.tool_calls} | "
                f"{run.usage.input_tokens} | {run.usage.output_tokens} | {run.latency_ms:.1f} | "
                f"{grounding.unsupported_count} | {grounding.proposed_count} | "
                f"{grounding.causality_overclaim_count} | {uncertainty} | ok"
            )
        return 2 if had_provider_errors else 0

    if args.command == "benchmark":
        return _run_reproducible_benchmark(args=args, store=store, model=model)

    pattern = AutonomyPattern(args.pattern)
    runner = _build_runner(pattern, store=store, model=model)
    results = repeat_pattern(runner, incident_id=args.incident, runs=args.runs)
    for run in results:
        _record_if_requested(run, args.trace_file)
    summary = summarize_repetitions(results)
    print(
        f"pattern={summary.pattern.value} runs={summary.runs} "
        f"unique_trajectories={summary.unique_trajectories}"
    )
    for index, trajectory in enumerate(summary.trajectories, start=1):
        print(f"run {index}: {' -> '.join(trajectory)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
