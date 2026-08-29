"""Application service for repeated, metadata-only architecture benchmarks."""

import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from statistics import fmean, median

from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.application.patterns.agent import AgentLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, PatternRun
from autonomy_lab.domain.benchmark import (
    BenchmarkConfig,
    BenchmarkRecord,
    BenchmarkStatus,
    PatternBenchmarkSummary,
)
from autonomy_lab.domain.epistemic import EpistemicReport, EpistemicVerdict
from autonomy_lab.domain.grounding import GroundingReport

RunPattern = Callable[[AutonomyPattern], PatternRun]
EvaluateRun = Callable[[PatternRun], GroundingReport]
EvaluateEpistemicRun = Callable[[PatternRun], EpistemicReport]
OnSuccess = Callable[[PatternRun], None]
Sleep = Callable[[float], None]
Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _rotated_patterns(
    patterns: Sequence[AutonomyPattern],
    *,
    run_number: int,
) -> tuple[AutonomyPattern, ...]:
    ordered = tuple(patterns)
    if not ordered:
        return ()
    offset = (run_number - 1) % len(ordered)
    return ordered[offset:] + ordered[:offset]


def run_benchmark(
    *,
    config: BenchmarkConfig,
    patterns: Sequence[AutonomyPattern],
    run_pattern: RunPattern,
    evaluate_run: EvaluateRun,
    evaluate_epistemic_run: EvaluateEpistemicRun | None = None,
    on_success: OnSuccess | None = None,
    sleep: Sleep = time.sleep,
    now: Now = _utc_now,
) -> tuple[BenchmarkRecord, ...]:
    """Execute repeated pattern cycles without hidden retries or answer persistence."""
    records: list[BenchmarkRecord] = []
    first_attempt = True

    for run_number in range(1, config.runs + 1):
        for pattern in _rotated_patterns(patterns, run_number=run_number):
            if not first_attempt and config.run_interval_seconds > 0:
                sleep(config.run_interval_seconds)
            first_attempt = False
            timestamp = now().isoformat()

            try:
                run = run_pattern(pattern)
            except ModelRateLimitError as exc:
                records.append(
                    _failure_record(
                        config=config,
                        timestamp=timestamp,
                        pattern=pattern,
                        run_number=run_number,
                        status=BenchmarkStatus.RATE_LIMITED,
                        error=exc,
                    )
                )
                continue
            except ModelProviderError as exc:
                records.append(
                    _failure_record(
                        config=config,
                        timestamp=timestamp,
                        pattern=pattern,
                        run_number=run_number,
                        status=BenchmarkStatus.PROVIDER_ERROR,
                        error=exc,
                    )
                )
                continue
            except AgentLimitError as exc:
                records.append(
                    _bound_exceeded_record(
                        config=config,
                        timestamp=timestamp,
                        pattern=pattern,
                        run_number=run_number,
                        error=exc,
                    )
                )
                continue

            if on_success is not None:
                on_success(run)
            grounding = evaluate_run(run)
            epistemic = (
                evaluate_epistemic_run(run) if evaluate_epistemic_run is not None else None
            )
            records.append(
                BenchmarkRecord(
                    timestamp_utc=timestamp,
                    git_commit=config.git_commit,
                    provider=config.provider,
                    model=config.model,
                    max_tokens=config.max_tokens,
                    timeout_seconds=config.timeout_seconds,
                    reasoning_effort=config.reasoning_effort,
                    run_interval_seconds=config.run_interval_seconds,
                    incident_id=config.incident_id,
                    pattern=pattern,
                    run_number=run_number,
                    status=BenchmarkStatus.OK,
                    model_calls=run.model_calls,
                    tool_calls=run.tool_calls,
                    input_tokens=run.usage.input_tokens,
                    output_tokens=run.usage.output_tokens,
                    latency_ms=run.latency_ms,
                    unsupported_count=grounding.unsupported_count,
                    proposed_count=grounding.proposed_count,
                    causality_overclaims=grounding.causality_overclaim_count,
                    grounding_ratio=grounding.specific_grounding_ratio,
                    uncertainty_preserved=grounding.uncertainty_preserved,
                    epistemic_expected_posture=(
                        epistemic.expected_posture if epistemic is not None else None
                    ),
                    epistemic_verdict=epistemic.verdict if epistemic is not None else None,
                    epistemic_aligned=epistemic.aligned if epistemic is not None else None,
                    causal_assertion_detected=(
                        epistemic.causal_assertion_detected if epistemic is not None else None
                    ),
                    hedged_causal_language_detected=(
                        epistemic.hedged_causal_language_detected
                        if epistemic is not None
                        else None
                    ),
                    abstention_detected=(
                        epistemic.abstention_detected if epistemic is not None else None
                    ),
                    uncertainty_language_detected=(
                        epistemic.uncertainty_language_detected if epistemic is not None else None
                    ),
                    trajectory=run.steps,
                )
            )

    return tuple(records)


def _failure_record(
    *,
    config: BenchmarkConfig,
    timestamp: str,
    pattern: AutonomyPattern,
    run_number: int,
    status: BenchmarkStatus,
    error: ModelProviderError,
) -> BenchmarkRecord:
    retry_after = error.retry_after if isinstance(error, ModelRateLimitError) else None
    return BenchmarkRecord(
        timestamp_utc=timestamp,
        git_commit=config.git_commit,
        provider=config.provider,
        model=config.model,
        max_tokens=config.max_tokens,
        timeout_seconds=config.timeout_seconds,
        reasoning_effort=config.reasoning_effort,
        run_interval_seconds=config.run_interval_seconds,
        incident_id=config.incident_id,
        pattern=pattern,
        run_number=run_number,
        status=status,
        retry_after=retry_after,
        error=str(error),
    )


def _bound_exceeded_record(
    *,
    config: BenchmarkConfig,
    timestamp: str,
    pattern: AutonomyPattern,
    run_number: int,
    error: AgentLimitError,
) -> BenchmarkRecord:
    return BenchmarkRecord(
        timestamp_utc=timestamp,
        git_commit=config.git_commit,
        provider=config.provider,
        model=config.model,
        max_tokens=config.max_tokens,
        timeout_seconds=config.timeout_seconds,
        reasoning_effort=config.reasoning_effort,
        run_interval_seconds=config.run_interval_seconds,
        incident_id=config.incident_id,
        pattern=pattern,
        run_number=run_number,
        status=BenchmarkStatus.BOUND_EXCEEDED,
        model_calls=error.model_calls,
        tool_calls=error.tool_calls,
        input_tokens=error.usage.input_tokens,
        output_tokens=error.usage.output_tokens,
        latency_ms=error.latency_ms,
        trajectory=error.steps,
        error=str(error),
    )


def summarize_benchmark(
    records: Sequence[BenchmarkRecord],
    *,
    patterns: Sequence[AutonomyPattern],
) -> tuple[PatternBenchmarkSummary, ...]:
    """Aggregate completed and failed attempts without imputing missing measurements."""
    summaries: list[PatternBenchmarkSummary] = []
    for pattern in patterns:
        attempted = [record for record in records if record.pattern is pattern]
        completed = [record for record in attempted if record.status is BenchmarkStatus.OK]
        rate_limited = sum(record.status is BenchmarkStatus.RATE_LIMITED for record in attempted)
        provider_errors = sum(
            record.status is BenchmarkStatus.PROVIDER_ERROR for record in attempted
        )
        bound_exceeded = sum(
            record.status is BenchmarkStatus.BOUND_EXCEEDED for record in attempted
        )
        total = len(attempted)
        completed_count = len(completed)
        epistemic_evaluated = sum(record.epistemic_verdict is not None for record in completed)
        epistemic_aligned = _epistemic_verdict_count(completed, EpistemicVerdict.ALIGNED)

        summaries.append(
            PatternBenchmarkSummary(
                pattern=pattern,
                attempted=total,
                completed=completed_count,
                rate_limited=rate_limited,
                provider_errors=provider_errors,
                bound_exceeded=bound_exceeded,
                completion_rate=_rate(completed_count, total),
                rate_limit_rate=_rate(rate_limited, total),
                provider_error_rate=_rate(provider_errors, total),
                bound_exceeded_rate=_rate(bound_exceeded, total),
                mean_model_calls=_mean(completed, "model_calls"),
                mean_tool_calls=_mean(completed, "tool_calls"),
                mean_input_tokens=_mean(completed, "input_tokens"),
                mean_output_tokens=_mean(completed, "output_tokens"),
                mean_total_tokens=_mean_total_tokens(completed),
                p50_latency_ms=_median(completed, "latency_ms"),
                mean_unsupported=_mean(completed, "unsupported_count"),
                mean_proposed=_mean(completed, "proposed_count"),
                mean_causality_overclaims=_mean(completed, "causality_overclaims"),
                mean_grounding_ratio=_mean(completed, "grounding_ratio"),
                uncertainty_preservation_rate=_uncertainty_rate(completed),
                epistemic_evaluated=epistemic_evaluated,
                epistemic_aligned=epistemic_aligned,
                epistemic_alignment_rate=(
                    _rate(epistemic_aligned, epistemic_evaluated)
                    if epistemic_evaluated
                    else None
                ),
                epistemic_overclaimed=_epistemic_verdict_count(
                    completed, EpistemicVerdict.OVERCLAIMED
                ),
                epistemic_over_hedged=_epistemic_verdict_count(
                    completed, EpistemicVerdict.OVER_HEDGED
                ),
                epistemic_insufficient_abstention=_epistemic_verdict_count(
                    completed, EpistemicVerdict.INSUFFICIENT_ABSTENTION
                ),
                epistemic_no_position=_epistemic_verdict_count(
                    completed, EpistemicVerdict.NO_POSITION
                ),
                unique_trajectories=len({record.trajectory for record in completed}),
            )
        )
    return tuple(summaries)


def _epistemic_verdict_count(
    records: Sequence[BenchmarkRecord],
    verdict: EpistemicVerdict,
) -> int:
    return sum(record.epistemic_verdict is verdict for record in records)


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _numeric_values(records: Sequence[BenchmarkRecord], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = getattr(record, field)
        if isinstance(value, bool) or value is None:
            continue
        values.append(float(value))
    return values


def _mean(records: Sequence[BenchmarkRecord], field: str) -> float | None:
    values = _numeric_values(records, field)
    return fmean(values) if values else None


def _median(records: Sequence[BenchmarkRecord], field: str) -> float | None:
    values = _numeric_values(records, field)
    return float(median(values)) if values else None


def _mean_total_tokens(records: Sequence[BenchmarkRecord]) -> float | None:
    values = [
        float(record.input_tokens + record.output_tokens)
        for record in records
        if record.input_tokens is not None and record.output_tokens is not None
    ]
    return fmean(values) if values else None


def _uncertainty_rate(records: Sequence[BenchmarkRecord]) -> float | None:
    values = [
        record.uncertainty_preserved
        for record in records
        if record.uncertainty_preserved is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)
