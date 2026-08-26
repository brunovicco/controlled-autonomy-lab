import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from autonomy_lab.adapters.benchmark_artifacts import write_benchmark_artifacts
from autonomy_lab.domain.autonomy import AutonomyPattern
from autonomy_lab.domain.benchmark import (
    BenchmarkConfig,
    BenchmarkRecord,
    BenchmarkStatus,
    PatternBenchmarkSummary,
)


def _config() -> BenchmarkConfig:
    return BenchmarkConfig(
        incident_id="INC-001",
        runs=1,
        provider="groq",
        model="openai/gpt-oss-20b",
        max_tokens=900,
        timeout_seconds=30.0,
        run_interval_seconds=2.0,
        git_commit="abc123",
    )


def _record() -> BenchmarkRecord:
    return BenchmarkRecord(
        timestamp_utc="2026-08-26T13:00:00+00:00",
        git_commit="abc123",
        provider="groq",
        model="openai/gpt-oss-20b",
        max_tokens=900,
        timeout_seconds=30.0,
        reasoning_effort=None,
        run_interval_seconds=2.0,
        incident_id="INC-001",
        pattern=AutonomyPattern.AGENT,
        run_number=1,
        status=BenchmarkStatus.OK,
        model_calls=5,
        tool_calls=4,
        input_tokens=2804,
        output_tokens=1161,
        latency_ms=5576.2,
        unsupported_count=2,
        proposed_count=3,
        causality_overclaims=0,
        grounding_ratio=0.846,
        uncertainty_preserved=True,
        trajectory=("get_service_metrics", "final-answer"),
    )


def _summary() -> PatternBenchmarkSummary:
    return PatternBenchmarkSummary(
        pattern=AutonomyPattern.AGENT,
        attempted=1,
        completed=1,
        rate_limited=0,
        provider_errors=0,
        completion_rate=1.0,
        rate_limit_rate=0.0,
        provider_error_rate=0.0,
        mean_model_calls=5.0,
        mean_tool_calls=4.0,
        mean_input_tokens=2804.0,
        mean_output_tokens=1161.0,
        mean_total_tokens=3965.0,
        p50_latency_ms=5576.2,
        mean_unsupported=2.0,
        mean_proposed=3.0,
        mean_causality_overclaims=0.0,
        mean_grounding_ratio=0.846,
        uncertainty_preservation_rate=1.0,
        unique_trajectories=1,
    )


def test_benchmark_artifacts_are_metadata_only(tmp_path: Path) -> None:
    artifacts = write_benchmark_artifacts(
        output_dir=tmp_path,
        config=_config(),
        records=(_record(),),
        summaries=(_summary(),),
    )

    payload = json.loads(artifacts.runs_jsonl.read_text(encoding="utf-8"))
    assert payload["pattern"] == "agent"
    assert payload["grounding_ratio"] == 0.846
    assert payload["trajectory"] == ["get_service_metrics", "final-answer"]
    assert "answer" not in payload
    assert "prompt" not in payload
    assert "evidence" not in payload

    with artifacts.summary_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["pattern"] == "agent"
    assert rows[0]["completed"] == "1"
    assert rows[0]["max_tokens"] == "900"
    assert rows[0]["timeout_seconds"] == "30.0"
    assert rows[0]["benchmark_status"] == "complete"

    markdown = artifacts.summary_markdown.read_text(encoding="utf-8")
    assert "# Reproducible Benchmark Summary" in markdown
    assert "only. It does not serialize" in markdown
    assert "Provider errors" in markdown
    assert "| agent | 1/1 | 5.0 | 4.0 | 3965 |" in markdown
    assert "parallel fan-out remains concurrent" in markdown


def test_partial_summary_surfaces_rate_limit_context(tmp_path: Path) -> None:
    rate_limited = replace(
        _record(),
        status=BenchmarkStatus.RATE_LIMITED,
        model_calls=None,
        tool_calls=None,
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
        unsupported_count=None,
        proposed_count=None,
        causality_overclaims=None,
        grounding_ratio=None,
        uncertainty_preserved=None,
        trajectory=(),
        retry_after="2",
        error="Groq API returned HTTP 429",
    )
    summary = replace(
        _summary(),
        completed=0,
        rate_limited=1,
        completion_rate=0.0,
        rate_limit_rate=1.0,
        mean_model_calls=None,
        mean_tool_calls=None,
        mean_input_tokens=None,
        mean_output_tokens=None,
        mean_total_tokens=None,
        p50_latency_ms=None,
        mean_unsupported=None,
        mean_proposed=None,
        mean_causality_overclaims=None,
        mean_grounding_ratio=None,
        uncertainty_preservation_rate=None,
        unique_trajectories=0,
    )

    artifacts = write_benchmark_artifacts(
        output_dir=tmp_path,
        config=_config(),
        records=(rate_limited,),
        summaries=(summary,),
    )

    markdown = artifacts.summary_markdown.read_text(encoding="utf-8")
    assert "Benchmark status: `partial`" in markdown
    assert "Rate limits occurred in this experiment." in markdown
    assert "increase the attempt interval" in markdown
    assert "| agent | 0/1 | - | - | - | - | - | - | - | - | 100.0% | 0.0% | 0 |" in markdown


def test_partial_summary_surfaces_provider_error_context(tmp_path: Path) -> None:
    provider_error = replace(
        _record(),
        status=BenchmarkStatus.PROVIDER_ERROR,
        model_calls=None,
        tool_calls=None,
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
        unsupported_count=None,
        proposed_count=None,
        causality_overclaims=None,
        grounding_ratio=None,
        uncertainty_preserved=None,
        trajectory=(),
        error=(
            "OpenAI API returned HTTP 400: type=invalid_request_error; "
            "message=tool message rejected"
        ),
    )
    summary = replace(
        _summary(),
        completed=0,
        provider_errors=1,
        completion_rate=0.0,
        provider_error_rate=1.0,
        mean_model_calls=None,
        mean_tool_calls=None,
        mean_input_tokens=None,
        mean_output_tokens=None,
        mean_total_tokens=None,
        p50_latency_ms=None,
        mean_unsupported=None,
        mean_proposed=None,
        mean_causality_overclaims=None,
        mean_grounding_ratio=None,
        uncertainty_preservation_rate=None,
        unique_trajectories=0,
    )

    artifacts = write_benchmark_artifacts(
        output_dir=tmp_path,
        config=_config(),
        records=(provider_error,),
        summaries=(summary,),
    )

    markdown = artifacts.summary_markdown.read_text(encoding="utf-8")
    assert "Benchmark status: `partial`" in markdown
    assert "Provider errors occurred in this experiment." in markdown
    assert "raw provider response bodies are not persisted" in markdown
    assert "| agent | 0/1 | - | - | - | - | - | - | - | - | 0.0% | 100.0% | 0 |" in markdown


def test_benchmark_artifacts_require_explicit_overwrite(tmp_path: Path) -> None:
    config = _config()
    records = (_record(),)
    summaries = (_summary(),)

    write_benchmark_artifacts(
        output_dir=tmp_path,
        config=config,
        records=records,
        summaries=summaries,
    )

    with pytest.raises(FileExistsError, match="--overwrite"):
        write_benchmark_artifacts(
            output_dir=tmp_path,
            config=config,
            records=records,
            summaries=summaries,
        )

    write_benchmark_artifacts(
        output_dir=tmp_path,
        config=config,
        records=records,
        summaries=summaries,
        overwrite=True,
    )
