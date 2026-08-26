from datetime import UTC, datetime

from autonomy_lab.application.benchmark import run_benchmark, summarize_benchmark
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun
from autonomy_lab.domain.benchmark import BenchmarkConfig, BenchmarkStatus
from autonomy_lab.domain.grounding import GroundingReport


def _config(*, runs: int = 2, interval: float = 1.5) -> BenchmarkConfig:
    return BenchmarkConfig(
        incident_id="INC-001",
        runs=runs,
        provider="groq",
        model="openai/gpt-oss-20b",
        max_tokens=900,
        timeout_seconds=30.0,
        run_interval_seconds=interval,
        git_commit="abc123",
    )


def _run(pattern: AutonomyPattern) -> PatternRun:
    return PatternRun(
        pattern=pattern,
        incident_id="INC-001",
        answer="grounded answer",
        model_calls=2,
        tool_calls=1 if pattern is AutonomyPattern.AGENT else 0,
        steps=("inspect", "final-answer"),
        usage=ModelUsage(input_tokens=20, output_tokens=5),
        latency_ms=12.5,
    )


def _grounding(run: PatternRun) -> GroundingReport:
    del run
    return GroundingReport(
        supported_specifics=("8.7%",),
        unsupported_specifics=(),
        causality_overclaims=(),
        uncertainty_preserved=True,
    )


def test_benchmark_interleaves_patterns_and_paces_between_attempts() -> None:
    calls: list[AutonomyPattern] = []
    sleeps: list[float] = []

    def execute(pattern: AutonomyPattern) -> PatternRun:
        calls.append(pattern)
        return _run(pattern)

    records = run_benchmark(
        config=_config(),
        patterns=(AutonomyPattern.AUGMENTED, AutonomyPattern.AGENT),
        run_pattern=execute,
        evaluate_run=_grounding,
        sleep=sleeps.append,
        now=lambda: datetime(2026, 8, 26, 13, 0, tzinfo=UTC),
    )

    assert calls == [
        AutonomyPattern.AUGMENTED,
        AutonomyPattern.AGENT,
        AutonomyPattern.AUGMENTED,
        AutonomyPattern.AGENT,
    ]
    assert sleeps == [1.5, 1.5, 1.5]
    assert len(records) == 4
    assert all(record.status is BenchmarkStatus.OK for record in records)
    assert records[0].run_number == 1
    assert records[2].run_number == 2


def test_benchmark_records_rate_limit_without_retrying() -> None:
    attempts = 0

    def execute(pattern: AutonomyPattern) -> PatternRun:
        nonlocal attempts
        attempts += 1
        if pattern is AutonomyPattern.CHAINING:
            raise ModelRateLimitError("Groq API returned HTTP 429", retry_after="2")
        return _run(pattern)

    records = run_benchmark(
        config=_config(runs=1, interval=0),
        patterns=(AutonomyPattern.AUGMENTED, AutonomyPattern.CHAINING),
        run_pattern=execute,
        evaluate_run=_grounding,
    )

    assert attempts == 2
    assert records[0].status is BenchmarkStatus.OK
    assert records[1].status is BenchmarkStatus.RATE_LIMITED
    assert records[1].retry_after == "2"
    assert records[1].model_calls is None


def test_benchmark_summary_uses_completed_runs_only() -> None:
    attempts = 0

    def execute(pattern: AutonomyPattern) -> PatternRun:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise ModelRateLimitError("rate limited")
        return _run(pattern)

    records = run_benchmark(
        config=_config(runs=2, interval=0),
        patterns=(AutonomyPattern.AUGMENTED,),
        run_pattern=execute,
        evaluate_run=_grounding,
    )
    (summary,) = summarize_benchmark(records, patterns=(AutonomyPattern.AUGMENTED,))

    assert summary.attempted == 2
    assert summary.completed == 1
    assert summary.rate_limited == 1
    assert summary.completion_rate == 0.5
    assert summary.rate_limit_rate == 0.5
    assert summary.mean_model_calls == 2.0
    assert summary.mean_total_tokens == 25.0
    assert summary.p50_latency_ms == 12.5
    assert summary.mean_grounding_ratio == 1.0
    assert summary.uncertainty_preservation_rate == 1.0
    assert summary.unique_trajectories == 1
