"""Command-line interface for the controlled-autonomy demonstration."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from autonomy_lab.adapters.anthropic import ModelProviderError as AnthropicProviderError
from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.providers import client_from_env
from autonomy_lab.adapters.run_log import MetadataRunRecorder
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

def _run_payload(run: PatternRun, grounding: GroundingReport | None = None) -> dict[str, object]:
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
    return payload


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


def _print_run(
    run: PatternRun,
    *,
    as_json: bool,
    grounding: GroundingReport | None = None,
) -> None:
    if as_json:
        print(json.dumps(_run_payload(run, grounding), indent=2))
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

    compare_parser = subparsers.add_parser("compare", help="execute every pattern once")
    compare_parser.add_argument("--incident", default="INC-001")

    repeat_parser = subparsers.add_parser("repeat", help="measure trajectory variance")
    repeat_parser.add_argument("pattern", choices=[pattern.value for pattern in AutonomyPattern])
    repeat_parser.add_argument("--incident", default="INC-001")
    repeat_parser.add_argument("--runs", type=int, default=5)
    return parser



def _print_compare_failure(pattern: AutonomyPattern, status: str) -> None:
    print(f"{pattern.value} | - | - | - | - | - | - | - | - | - | {status}")
def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process exit code."""
    args = _parser().parse_args(argv)
    store = InMemoryIncidentStore()
    model = _client_from_env()

    if args.command == "run":
        pattern = AutonomyPattern(args.pattern)
        run = _build_runner(pattern, store=store, model=model).run(args.incident)
        _record_if_requested(run, args.trace_file)
        grounding = None
        if args.grounding:
            grounding = _grounding_for_run(
                run,
                store=store,
                evaluator=DeterministicGroundingEvaluator(),
            )
        _print_run(run, as_json=args.json, grounding=grounding)
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
        except (ModelProviderError, AnthropicProviderError):
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
