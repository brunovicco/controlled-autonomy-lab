"""Command-line interface for the controlled-autonomy demonstration."""

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from harness_example.adapters.anthropic import AnthropicMessagesClient
from harness_example.adapters.incidents import InMemoryIncidentStore
from harness_example.adapters.run_log import MetadataRunRecorder
from harness_example.application.comparison import PatternRunner, repeat_pattern, summarize_repetitions
from harness_example.application.patterns.agent import BoundedIncidentAgent
from harness_example.application.patterns.augmented import AugmentedIncidentAnalysis
from harness_example.application.patterns.chaining import ChainedIncidentAnalysis
from harness_example.application.patterns.evaluator_optimizer import EvaluatorOptimizerIncidentAnalysis
from harness_example.application.patterns.parallel import ParallelIncidentAnalysis
from harness_example.application.patterns.routing import RoutedIncidentAnalysis
from harness_example.domain.autonomy import AutonomyPattern, PatternRun


def _build_runner(
    pattern: AutonomyPattern,
    *,
    store: InMemoryIncidentStore,
    model: AnthropicMessagesClient,
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


def _client_from_env() -> AnthropicMessagesClient:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required for live runs")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
    return AnthropicMessagesClient(api_key=api_key, model=model)


def _run_payload(run: PatternRun) -> dict[str, object]:
    return {
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


def _print_run(run: PatternRun, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(_run_payload(run), indent=2))
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


def _record_if_requested(run: PatternRun, trace_file: str | None) -> None:
    if trace_file:
        MetadataRunRecorder(Path(trace_file)).append(run)


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

    compare_parser = subparsers.add_parser("compare", help="execute every pattern once")
    compare_parser.add_argument("--incident", default="INC-001")

    repeat_parser = subparsers.add_parser("repeat", help="measure trajectory variance")
    repeat_parser.add_argument("pattern", choices=[pattern.value for pattern in AutonomyPattern])
    repeat_parser.add_argument("--incident", default="INC-001")
    repeat_parser.add_argument("--runs", type=int, default=5)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CLI and return a process exit code."""
    args = _parser().parse_args(argv)
    store = InMemoryIncidentStore()
    model = _client_from_env()

    if args.command == "run":
        pattern = AutonomyPattern(args.pattern)
        run = _build_runner(pattern, store=store, model=model).run(args.incident)
        _record_if_requested(run, args.trace_file)
        _print_run(run, as_json=args.json)
        return 0

    if args.command == "compare":
        print("pattern | model_calls | tool_calls | input_tokens | output_tokens | latency_ms")
        print("-" * 82)
        for pattern in AutonomyPattern:
            run = _build_runner(pattern, store=store, model=model).run(args.incident)
            _record_if_requested(run, args.trace_file)
            print(
                f"{pattern.value} | {run.model_calls} | {run.tool_calls} | "
                f"{run.usage.input_tokens} | {run.usage.output_tokens} | {run.latency_ms:.1f}"
            )
        return 0

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
