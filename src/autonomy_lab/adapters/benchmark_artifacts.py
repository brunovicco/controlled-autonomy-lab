"""Persistence adapter for reproducible benchmark artifacts."""

import csv
import json
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from autonomy_lab.domain.benchmark import (
    BENCHMARK_RECORD_SCHEMA_VERSION,
    BENCHMARK_SUMMARY_SCHEMA_VERSION,
    EPISTEMIC_EVALUATION_VERSION,
    GROUNDING_EVALUATION_VERSION,
    BenchmarkConfig,
    BenchmarkRecord,
    BenchmarkStatus,
    PatternBenchmarkSummary,
)


@dataclass(frozen=True, slots=True)
class BenchmarkArtifacts:
    """Paths written by one benchmark execution."""

    runs_jsonl: Path
    summary_csv: Path
    summary_markdown: Path


def benchmark_artifact_paths(output_dir: Path) -> BenchmarkArtifacts:
    """Return the canonical benchmark artifact paths for one output directory."""
    return BenchmarkArtifacts(
        runs_jsonl=output_dir / "runs.jsonl",
        summary_csv=output_dir / "summary.csv",
        summary_markdown=output_dir / "summary.md",
    )


def assert_benchmark_output_available(output_dir: Path, *, overwrite: bool = False) -> None:
    """Fail before provider calls when benchmark output would be overwritten."""
    if overwrite:
        return
    artifacts = benchmark_artifact_paths(output_dir)
    existing = [
        path
        for path in (
            artifacts.runs_jsonl,
            artifacts.summary_csv,
            artifacts.summary_markdown,
        )
        if path.exists()
    ]
    if existing:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(f"benchmark output already exists: {names}; use --overwrite")


def write_benchmark_artifacts(
    *,
    output_dir: Path,
    config: BenchmarkConfig,
    records: tuple[BenchmarkRecord, ...],
    summaries: tuple[PatternBenchmarkSummary, ...],
    overwrite: bool = False,
) -> BenchmarkArtifacts:
    """Persist metadata-only raw records plus machine- and human-readable summaries."""
    assert_benchmark_output_available(output_dir, overwrite=overwrite)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = benchmark_artifact_paths(output_dir)

    jsonl = "".join(
        f"{json.dumps(_record_payload(record), sort_keys=True)}\n" for record in records
    )
    _atomic_write(artifacts.runs_jsonl, jsonl)
    _atomic_write(
        artifacts.summary_csv,
        _summary_csv(config=config, summaries=summaries),
    )
    _atomic_write(
        artifacts.summary_markdown,
        _summary_markdown(config=config, records=records, summaries=summaries),
    )
    return artifacts


def _record_payload(record: BenchmarkRecord) -> dict[str, Any]:
    return {
        "schema_version": BENCHMARK_RECORD_SCHEMA_VERSION,
        "grounding_evaluation_version": GROUNDING_EVALUATION_VERSION,
        "epistemic_evaluation_version": EPISTEMIC_EVALUATION_VERSION,
        "timestamp_utc": record.timestamp_utc,
        "git_commit": record.git_commit,
        "provider": record.provider,
        "model": record.model,
        "max_tokens": record.max_tokens,
        "timeout_seconds": record.timeout_seconds,
        "reasoning_effort": record.reasoning_effort,
        "run_interval_seconds": record.run_interval_seconds,
        "incident_id": record.incident_id,
        "pattern": record.pattern.value,
        "run_number": record.run_number,
        "status": record.status.value,
        "model_calls": record.model_calls,
        "tool_calls": record.tool_calls,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "latency_ms": _rounded(record.latency_ms),
        "unsupported_count": record.unsupported_count,
        "proposed_count": record.proposed_count,
        "causality_overclaims": record.causality_overclaims,
        "grounding_ratio": _rounded(record.grounding_ratio, digits=4),
        "uncertainty_preserved": record.uncertainty_preserved,
        "epistemic_expected_posture": (
            record.epistemic_expected_posture.value
            if record.epistemic_expected_posture is not None
            else None
        ),
        "epistemic_verdict": (
            record.epistemic_verdict.value if record.epistemic_verdict is not None else None
        ),
        "epistemic_aligned": record.epistemic_aligned,
        "causal_assertion_detected": record.causal_assertion_detected,
        "hedged_causal_language_detected": record.hedged_causal_language_detected,
        "abstention_detected": record.abstention_detected,
        "uncertainty_language_detected": record.uncertainty_language_detected,
        "trajectory": list(record.trajectory),
        "retry_after": record.retry_after,
        "error": record.error,
    }


def _summary_csv(
    *,
    config: BenchmarkConfig,
    summaries: tuple[PatternBenchmarkSummary, ...],
) -> str:
    fieldnames = [
        "schema_version",
        "grounding_evaluation_version",
        "epistemic_evaluation_version",
        "git_commit",
        "provider",
        "model",
        "max_tokens",
        "timeout_seconds",
        "reasoning_effort",
        "incident_id",
        "runs",
        "run_interval_seconds",
        "benchmark_status",
        "pattern",
        "attempted",
        "completed",
        "rate_limited",
        "provider_errors",
        "bound_exceeded",
        "completion_rate",
        "rate_limit_rate",
        "provider_error_rate",
        "bound_exceeded_rate",
        "mean_model_calls",
        "mean_tool_calls",
        "mean_input_tokens",
        "mean_output_tokens",
        "mean_total_tokens",
        "p50_latency_ms",
        "mean_unsupported",
        "mean_proposed",
        "mean_causality_overclaims",
        "mean_grounding_ratio",
        "uncertainty_preservation_rate",
        "epistemic_evaluated",
        "epistemic_aligned",
        "epistemic_alignment_rate",
        "epistemic_overclaimed",
        "epistemic_over_hedged",
        "epistemic_insufficient_abstention",
        "epistemic_no_position",
        "unique_trajectories",
    ]
    status = _benchmark_status_from_summaries(summaries)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for summary in summaries:
        writer.writerow(
            {
                "schema_version": BENCHMARK_SUMMARY_SCHEMA_VERSION,
                "grounding_evaluation_version": GROUNDING_EVALUATION_VERSION,
                "epistemic_evaluation_version": EPISTEMIC_EVALUATION_VERSION,
                "git_commit": config.git_commit,
                "provider": config.provider,
                "model": config.model,
                "max_tokens": config.max_tokens,
                "timeout_seconds": config.timeout_seconds,
                "reasoning_effort": config.reasoning_effort or "",
                "incident_id": config.incident_id,
                "runs": config.runs,
                "run_interval_seconds": config.run_interval_seconds,
                "benchmark_status": status,
                "pattern": summary.pattern.value,
                "attempted": summary.attempted,
                "completed": summary.completed,
                "rate_limited": summary.rate_limited,
                "provider_errors": summary.provider_errors,
                "bound_exceeded": summary.bound_exceeded,
                "completion_rate": _csv_number(summary.completion_rate),
                "rate_limit_rate": _csv_number(summary.rate_limit_rate),
                "provider_error_rate": _csv_number(summary.provider_error_rate),
                "bound_exceeded_rate": _csv_number(summary.bound_exceeded_rate),
                "mean_model_calls": _csv_number(summary.mean_model_calls),
                "mean_tool_calls": _csv_number(summary.mean_tool_calls),
                "mean_input_tokens": _csv_number(summary.mean_input_tokens),
                "mean_output_tokens": _csv_number(summary.mean_output_tokens),
                "mean_total_tokens": _csv_number(summary.mean_total_tokens),
                "p50_latency_ms": _csv_number(summary.p50_latency_ms),
                "mean_unsupported": _csv_number(summary.mean_unsupported),
                "mean_proposed": _csv_number(summary.mean_proposed),
                "mean_causality_overclaims": _csv_number(summary.mean_causality_overclaims),
                "mean_grounding_ratio": _csv_number(summary.mean_grounding_ratio),
                "uncertainty_preservation_rate": _csv_number(summary.uncertainty_preservation_rate),
                "epistemic_evaluated": summary.epistemic_evaluated,
                "epistemic_aligned": summary.epistemic_aligned,
                "epistemic_alignment_rate": _csv_number(summary.epistemic_alignment_rate),
                "epistemic_overclaimed": summary.epistemic_overclaimed,
                "epistemic_over_hedged": summary.epistemic_over_hedged,
                "epistemic_insufficient_abstention": summary.epistemic_insufficient_abstention,
                "epistemic_no_position": summary.epistemic_no_position,
                "unique_trajectories": summary.unique_trajectories,
            }
        )
    return buffer.getvalue()


def _summary_markdown(
    *,
    config: BenchmarkConfig,
    records: tuple[BenchmarkRecord, ...],
    summaries: tuple[PatternBenchmarkSummary, ...],
) -> str:
    partial = any(record.status is not BenchmarkStatus.OK for record in records)
    rate_limited = any(record.status is BenchmarkStatus.RATE_LIMITED for record in records)
    provider_errors = any(record.status is BenchmarkStatus.PROVIDER_ERROR for record in records)
    bound_exceeded = any(record.status is BenchmarkStatus.BOUND_EXCEEDED for record in records)
    reasoning = config.reasoning_effort or "default/provider-defined"
    lines = [
        "# Reproducible Benchmark Summary",
        "",
        f"- Summary schema: `{BENCHMARK_SUMMARY_SCHEMA_VERSION}`",
        f"- Grounding evaluator: `{GROUNDING_EVALUATION_VERSION}`",
        f"- Epistemic evaluator: `{EPISTEMIC_EVALUATION_VERSION}`",
        f"- Git commit: `{config.git_commit}`",
        f"- Provider: `{config.provider}`",
        f"- Model: `{config.model}`",
        f"- Incident: `{config.incident_id}`",
        f"- Repetitions per pattern: `{config.runs}`",
        f"- Max output tokens: `{config.max_tokens}`",
        f"- Timeout: `{config.timeout_seconds:g}s`",
        f"- Reasoning effort: `{reasoning}`",
        f"- Interval between benchmark attempts: `{config.run_interval_seconds:g}s`",
        f"- Benchmark status: `{'partial' if partial else 'complete'}`",
        "",
        (
            "The interval applies between benchmark attempts only. It does not serialize "
            "calls inside a pattern; parallel fan-out remains concurrent and multi-call "
            "patterns retain their original behavior."
        ),
        "",
        (
            "Epistemic aggregates are computed only from successful cells carrying an "
            "`epistemic-v4.1` verdict. Provider failures and bounded-agent exhaustion are "
            "availability/runtime evidence, not quality zeros."
        ),
    ]
    if rate_limited:
        lines.extend(
            [
                "",
                (
                    "Rate limits occurred in this experiment. Keep them as benchmark evidence; "
                    "for a separate experiment, increase the attempt interval rather than "
                    "rerunning only the missing patterns."
                ),
            ]
        )
    if provider_errors:
        lines.extend(
            [
                "",
                (
                    "Provider errors occurred in this experiment. Safe bounded diagnostics are "
                    "recorded in `runs.jsonl`; raw provider response bodies are not persisted."
                ),
            ]
        )
    if bound_exceeded:
        lines.extend(
            [
                "",
                (
                    "Bound-exceeded attempts are retained as runtime evidence with partial "
                    "metadata. They are excluded from grounding and epistemic quality aggregates."
                ),
            ]
        )
    lines.extend(
        [
            "",
            (
                "| Pattern | Success | Calls | Tools | Avg tokens | p50 latency | Grounding | "
                "Epistemic aligned | Overclaim | Over-hedged | Need abstain | No position | "
                "Rate limited | Provider errors | Bound exceeded | Trajectories |"
            ),
            (
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
                "---: | ---: | ---: | ---: | ---: | ---: |"
            ),
        ]
    )
    for summary in summaries:
        lines.append(
            "| "
            + " | ".join(
                [
                    summary.pattern.value,
                    f"{summary.completed}/{summary.attempted}",
                    _md_number(summary.mean_model_calls),
                    _md_number(summary.mean_tool_calls),
                    _md_number(summary.mean_total_tokens, digits=0),
                    _md_number(summary.p50_latency_ms, suffix=" ms"),
                    _md_percent(summary.mean_grounding_ratio),
                    _md_percent(summary.epistemic_alignment_rate),
                    str(summary.epistemic_overclaimed),
                    str(summary.epistemic_over_hedged),
                    str(summary.epistemic_insufficient_abstention),
                    str(summary.epistemic_no_position),
                    _md_percent(summary.rate_limit_rate),
                    _md_percent(summary.provider_error_rate),
                    _md_percent(summary.bound_exceeded_rate),
                    str(summary.unique_trajectories),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            (
                "`runs.jsonl` and `summary.csv` are metadata-only. They do not contain "
                "prompts, model answers, evidence bodies, tool arguments/results, or credentials."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _benchmark_status_from_summaries(
    summaries: tuple[PatternBenchmarkSummary, ...],
) -> str:
    partial = any(summary.completed != summary.attempted for summary in summaries)
    return "partial" if partial else "complete"


def _rounded(value: float | None, *, digits: int = 3) -> float | None:
    return round(value, digits) if value is not None else None


def _csv_number(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def _md_number(value: float | None, *, digits: int = 1, suffix: str = "") -> str:
    return "-" if value is None else f"{value:.{digits}f}{suffix}"


def _md_percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1%}"


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
