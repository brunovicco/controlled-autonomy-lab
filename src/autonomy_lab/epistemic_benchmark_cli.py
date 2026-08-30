"""Dedicated runner for new benchmark generations with Epistemic Evaluation v4.1."""

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from autonomy_lab.adapters.benchmark_artifacts import (
    assert_benchmark_output_available,
    write_benchmark_artifacts,
)
from autonomy_lab.adapters.benchmark_metadata import benchmark_environment_from_env
from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.providers import client_from_env
from autonomy_lab.application.benchmark import run_benchmark, summarize_benchmark
from autonomy_lab.application.comparison import PatternRunner
from autonomy_lab.application.epistemic import DeterministicEpistemicEvaluator
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
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
from autonomy_lab.domain.benchmark import (
    BENCHMARK_RECORD_SCHEMA_VERSION,
    BENCHMARK_SUMMARY_SCHEMA_VERSION,
    BREADTH_MANIFEST_SCHEMA_VERSION,
    EPISTEMIC_EVALUATION_VERSION,
    GROUNDING_EVALUATION_VERSION,
    BenchmarkConfig,
    BenchmarkRecord,
    BenchmarkStatus,
    PatternBenchmarkSummary,
)
from autonomy_lab.domain.epistemic import EpistemicReport
from autonomy_lab.domain.grounding import GroundingReport

BREADTH_INCIDENTS = ("INC-001", "INC-002", "INC-003", "INC-004")


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
        prog="autonomy-lab-epistemic-benchmark",
        description=(
            "Run a new metadata-only benchmark generation with Grounding v1 and "
            "Epistemic Evaluation v4.1."
        ),
    )
    incidents = parser.add_mutually_exclusive_group()
    incidents.add_argument("--incident", default="INC-001")
    incidents.add_argument(
        "--all-incidents",
        action="store_true",
        help="run the canonical four-incident breadth suite",
    )
    parser.add_argument("--runs", type=_positive_int, default=1)
    parser.add_argument("--output", default="results/epistemic-v4-1")
    parser.add_argument(
        "--run-interval-seconds",
        type=_non_negative_float,
        default=0.0,
        help="pause between benchmark attempts without changing calls inside a pattern",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace benchmark artifacts when they already exist",
    )
    return parser


def _config(
    *,
    incident_id: str,
    runs: int,
    run_interval_seconds: float,
) -> BenchmarkConfig:
    environment = benchmark_environment_from_env()
    return BenchmarkConfig(
        incident_id=incident_id,
        runs=runs,
        provider=environment.provider,
        model=environment.model,
        max_tokens=environment.max_tokens,
        timeout_seconds=environment.timeout_seconds,
        reasoning_effort=environment.reasoning_effort,
        run_interval_seconds=run_interval_seconds,
        git_commit=environment.git_commit,
        epistemic_evaluation_version=EPISTEMIC_EVALUATION_VERSION,
    )


def _evaluate_grounding(
    run: PatternRun,
    *,
    store: InMemoryIncidentStore,
    evaluator: DeterministicGroundingEvaluator,
) -> GroundingReport:
    incident = store.get_incident(run.incident_id)
    evidence = store.get_evidence(incident)
    return evaluator.evaluate(answer=run.answer, incident=incident, evidence=evidence)


def _evaluate_epistemic(
    run: PatternRun,
    *,
    store: InMemoryIncidentStore,
    evaluator: DeterministicEpistemicEvaluator,
) -> EpistemicReport:
    incident = store.get_incident(run.incident_id)
    evidence = store.get_evidence(incident)
    return evaluator.evaluate(answer=run.answer, incident=incident, evidence=evidence)


def _run_incident(
    *,
    config: BenchmarkConfig,
    patterns: tuple[AutonomyPattern, ...],
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> tuple[tuple[BenchmarkRecord, ...], tuple[PatternBenchmarkSummary, ...]]:
    grounding_evaluator = DeterministicGroundingEvaluator()
    epistemic_evaluator = DeterministicEpistemicEvaluator()

    def execute(pattern: AutonomyPattern) -> PatternRun:
        return _build_runner(pattern, store=store, model=model).run(config.incident_id)

    def grounding(run: PatternRun) -> GroundingReport:
        return _evaluate_grounding(run, store=store, evaluator=grounding_evaluator)

    def epistemic(run: PatternRun) -> EpistemicReport:
        return _evaluate_epistemic(run, store=store, evaluator=epistemic_evaluator)

    records = run_benchmark(
        config=config,
        patterns=patterns,
        run_pattern=execute,
        evaluate_run=grounding,
        evaluate_epistemic_run=epistemic,
    )
    summaries = summarize_benchmark(records, patterns=tuple(AutonomyPattern))
    return records, summaries


def _rotated_patterns(incident_index: int) -> tuple[AutonomyPattern, ...]:
    patterns = tuple(AutonomyPattern)
    offset = incident_index % len(patterns)
    return patterns[offset:] + patterns[:offset]


def _manifest_summary(summary: PatternBenchmarkSummary) -> dict[str, object]:
    return {
        "pattern": summary.pattern.value,
        "attempted": summary.attempted,
        "completed": summary.completed,
        "rate_limited": summary.rate_limited,
        "provider_errors": summary.provider_errors,
        "bound_exceeded": summary.bound_exceeded,
        "mean_model_calls": summary.mean_model_calls,
        "mean_tool_calls": summary.mean_tool_calls,
        "mean_total_tokens": summary.mean_total_tokens,
        "p50_latency_ms": summary.p50_latency_ms,
        "mean_causality_overclaims": summary.mean_causality_overclaims,
        "mean_grounding_ratio": summary.mean_grounding_ratio,
        "epistemic_evaluated": summary.epistemic_evaluated,
        "epistemic_aligned": summary.epistemic_aligned,
        "epistemic_alignment_rate": summary.epistemic_alignment_rate,
        "epistemic_overclaimed": summary.epistemic_overclaimed,
        "epistemic_over_hedged": summary.epistemic_over_hedged,
        "epistemic_insufficient_abstention": summary.epistemic_insufficient_abstention,
        "epistemic_no_position": summary.epistemic_no_position,
        "unique_trajectories": summary.unique_trajectories,
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _run_breadth(
    *,
    args: argparse.Namespace,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> int:
    output_dir = Path(args.output)
    manifest_path = output_dir / "breadth-manifest.json"
    if manifest_path.exists() and not args.overwrite:
        print(
            f"breadth benchmark output already exists: {manifest_path.name}; use --overwrite",
            file=sys.stderr,
        )
        return 2

    plans: list[tuple[str, BenchmarkConfig, tuple[AutonomyPattern, ...], Path]] = []
    for incident_index, incident_id in enumerate(BREADTH_INCIDENTS):
        incident_output = output_dir / incident_id
        try:
            assert_benchmark_output_available(incident_output, overwrite=args.overwrite)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        plans.append(
            (
                incident_id,
                _config(
                    incident_id=incident_id,
                    runs=args.runs,
                    run_interval_seconds=args.run_interval_seconds,
                ),
                _rotated_patterns(incident_index),
                incident_output,
            )
        )

    completed_plans: list[
        tuple[
            str,
            BenchmarkConfig,
            tuple[BenchmarkRecord, ...],
            tuple[PatternBenchmarkSummary, ...],
            Path,
        ]
    ] = []
    for incident_index, (incident_id, config, patterns, incident_output) in enumerate(plans):
        if incident_index > 0 and args.run_interval_seconds > 0:
            time.sleep(args.run_interval_seconds)
        records, summaries = _run_incident(
            config=config,
            patterns=patterns,
            store=store,
            model=model,
        )
        completed_plans.append((incident_id, config, records, summaries, incident_output))

    for _, config, records, summaries, incident_output in completed_plans:
        write_benchmark_artifacts(
            output_dir=incident_output,
            config=config,
            records=records,
            summaries=summaries,
            overwrite=args.overwrite,
        )

    all_records = tuple(record for _, _, records, _, _ in completed_plans for record in records)
    aggregate = summarize_benchmark(all_records, patterns=tuple(AutonomyPattern))
    partial = any(record.status is not BenchmarkStatus.OK for record in all_records)
    completed = sum(record.status is BenchmarkStatus.OK for record in all_records)
    rate_limited = sum(record.status is BenchmarkStatus.RATE_LIMITED for record in all_records)
    provider_errors = sum(record.status is BenchmarkStatus.PROVIDER_ERROR for record in all_records)
    bound_exceeded = sum(record.status is BenchmarkStatus.BOUND_EXCEEDED for record in all_records)
    epistemic_evaluated = sum(summary.epistemic_evaluated for summary in aggregate)
    epistemic_aligned = sum(summary.epistemic_aligned for summary in aggregate)
    first_config = completed_plans[0][1]

    manifest: dict[str, object] = {
        "schema_version": BREADTH_MANIFEST_SCHEMA_VERSION,
        "record_schema_version": BENCHMARK_RECORD_SCHEMA_VERSION,
        "summary_schema_version": BENCHMARK_SUMMARY_SCHEMA_VERSION,
        "grounding_evaluation_version": GROUNDING_EVALUATION_VERSION,
        "epistemic_evaluation_version": EPISTEMIC_EVALUATION_VERSION,
        "generation_boundary": (
            "new generation; do not append these verdicts to frozen breadth-v1 quality aggregates"
        ),
        "git_commit": first_config.git_commit,
        "provider": first_config.provider,
        "model": first_config.model,
        "max_tokens": first_config.max_tokens,
        "timeout_seconds": first_config.timeout_seconds,
        "reasoning_effort": first_config.reasoning_effort or "default/provider-defined",
        "runs_per_incident_pattern": args.runs,
        "run_interval_seconds": args.run_interval_seconds,
        "incidents": list(BREADTH_INCIDENTS),
        "patterns": [pattern.value for pattern in AutonomyPattern],
        "attempted": len(all_records),
        "completed": completed,
        "rate_limited": rate_limited,
        "provider_errors": provider_errors,
        "bound_exceeded": bound_exceeded,
        "epistemic_evaluated": epistemic_evaluated,
        "epistemic_aligned": epistemic_aligned,
        "status": "partial" if partial else "complete",
        "aggregate_by_pattern": [_manifest_summary(summary) for summary in aggregate],
        "artifacts": {
            incident_id: {
                "runs_jsonl": str(incident_output / "runs.jsonl"),
                "summary_csv": str(incident_output / "summary.csv"),
                "summary_markdown": str(incident_output / "summary.md"),
            }
            for incident_id, _, _, _, incident_output in completed_plans
        },
    }
    _write_manifest(manifest_path, manifest)

    print(f"epistemic breadth benchmark: {'partial' if partial else 'complete'}")
    print(f"provider:          {first_config.provider}")
    print(f"model:             {first_config.model}")
    print(f"commit:            {first_config.git_commit}")
    print(f"attempts:          {len(all_records)}")
    print(f"completed:         {completed}")
    print(f"epistemic evals:   {epistemic_evaluated}")
    print(f"manifest:          {manifest_path}")
    return 2 if partial else 0


def _run_single(
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

    config = _config(
        incident_id=args.incident,
        runs=args.runs,
        run_interval_seconds=args.run_interval_seconds,
    )
    records, summaries = _run_incident(
        config=config,
        patterns=tuple(AutonomyPattern),
        store=store,
        model=model,
    )
    artifacts = write_benchmark_artifacts(
        output_dir=output_dir,
        config=config,
        records=records,
        summaries=summaries,
        overwrite=args.overwrite,
    )
    partial = any(record.status is not BenchmarkStatus.OK for record in records)
    print(f"epistemic benchmark: {'partial' if partial else 'complete'}")
    print(f"commit:             {config.git_commit}")
    print(f"jsonl:              {artifacts.runs_jsonl}")
    print(f"csv:                {artifacts.summary_csv}")
    print(f"markdown:           {artifacts.summary_markdown}")
    return 2 if partial else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a new epistemic benchmark generation and return a process exit code."""
    args = _parser().parse_args(argv)
    store = InMemoryIncidentStore()
    model = client_from_env()
    if args.all_incidents:
        return _run_breadth(args=args, store=store, model=model)
    return _run_single(args=args, store=store, model=model)


if __name__ == "__main__":
    raise SystemExit(main())
