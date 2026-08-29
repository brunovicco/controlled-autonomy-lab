from datetime import UTC, datetime

import pytest

from autonomy_lab.application.benchmark import run_benchmark, summarize_benchmark
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.application.patterns.agent import AgentLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun
from autonomy_lab.domain.benchmark import (
    EPISTEMIC_EVALUATION_VERSION,
    BenchmarkConfig,
    BenchmarkStatus,
)
from autonomy_lab.domain.epistemic import EpistemicReport, EpistemicVerdict, EvidencePosture
from autonomy_lab.domain.grounding import GroundingReport


def _config(*, epistemic: bool = True) -> BenchmarkConfig:
    return BenchmarkConfig(
        incident_id="INC-004",
        runs=1,
        provider="openai",
        model="gpt-5.6-luna",
        max_tokens=4000,
        timeout_seconds=60.0,
        run_interval_seconds=0.0,
        git_commit="freeze-v2",
        epistemic_evaluation_version=(EPISTEMIC_EVALUATION_VERSION if epistemic else None),
    )


def _run(pattern: AutonomyPattern = AutonomyPattern.AUGMENTED) -> PatternRun:
    return PatternRun(
        pattern=pattern,
        incident_id="INC-004",
        answer="The dependency likely caused the incident.",
        model_calls=1,
        tool_calls=0,
        steps=("final-answer",),
        usage=ModelUsage(input_tokens=100, output_tokens=25),
        latency_ms=15.0,
    )


def _grounding(run: PatternRun) -> GroundingReport:
    del run
    return GroundingReport(
        supported_specifics=(),
        unsupported_specifics=(),
        causality_overclaims=(),
        uncertainty_preserved=True,
    )


def _epistemic(run: PatternRun) -> EpistemicReport:
    del run
    return EpistemicReport(
        expected_posture=EvidencePosture.INCONCLUSIVE,
        verdict=EpistemicVerdict.INSUFFICIENT_ABSTENTION,
        causal_assertion_detected=False,
        hedged_causal_language_detected=True,
        abstention_detected=False,
        uncertainty_language_detected=True,
        causality_overclaim_count=0,
    )


def test_benchmark_records_epistemic_metadata_only_on_success() -> None:
    records = run_benchmark(
        config=_config(),
        patterns=(AutonomyPattern.AUGMENTED,),
        run_pattern=lambda pattern: _run(pattern),
        evaluate_run=_grounding,
        evaluate_epistemic_run=_epistemic,
        now=lambda: datetime(2026, 8, 29, 21, 0, tzinfo=UTC),
    )

    (record,) = records
    assert record.status is BenchmarkStatus.OK
    assert record.epistemic_evaluation_version == EPISTEMIC_EVALUATION_VERSION
    assert record.epistemic_expected_posture is EvidencePosture.INCONCLUSIVE
    assert record.epistemic_verdict is EpistemicVerdict.INSUFFICIENT_ABSTENTION
    assert record.epistemic_aligned is False
    assert record.hedged_causal_language_detected is True
    assert record.abstention_detected is False
    assert record.uncertainty_language_detected is True

    (summary,) = summarize_benchmark(records, patterns=(AutonomyPattern.AUGMENTED,))
    assert summary.epistemic_evaluated == 1
    assert summary.epistemic_aligned == 0
    assert summary.epistemic_alignment_rate == 0.0
    assert summary.epistemic_insufficient_abstention == 1


def test_benchmark_rejects_epistemic_callback_without_matching_provenance() -> None:
    with pytest.raises(ValueError, match="epistemic evaluator callback requires"):
        run_benchmark(
            config=_config(epistemic=False),
            patterns=(AutonomyPattern.AUGMENTED,),
            run_pattern=lambda pattern: _run(pattern),
            evaluate_run=_grounding,
            evaluate_epistemic_run=_epistemic,
        )


def test_provider_failure_keeps_version_but_has_no_quality_verdict() -> None:
    epistemic_calls = 0

    def fail(pattern: AutonomyPattern) -> PatternRun:
        del pattern
        raise ModelRateLimitError("HTTP 429", retry_after="5")

    def epistemic(run: PatternRun) -> EpistemicReport:
        nonlocal epistemic_calls
        epistemic_calls += 1
        return _epistemic(run)

    records = run_benchmark(
        config=_config(),
        patterns=(AutonomyPattern.AUGMENTED,),
        run_pattern=fail,
        evaluate_run=_grounding,
        evaluate_epistemic_run=epistemic,
    )

    (record,) = records
    assert epistemic_calls == 0
    assert record.status is BenchmarkStatus.RATE_LIMITED
    assert record.epistemic_evaluation_version == EPISTEMIC_EVALUATION_VERSION
    assert record.epistemic_verdict is None
    assert record.epistemic_aligned is None

    (summary,) = summarize_benchmark(records, patterns=(AutonomyPattern.AUGMENTED,))
    assert summary.epistemic_evaluated == 0
    assert summary.epistemic_alignment_rate is None


def test_bound_exceeded_is_counted_as_runtime_evidence_not_quality() -> None:
    def exceed(pattern: AutonomyPattern) -> PatternRun:
        del pattern
        raise AgentLimitError(
            "agent exceeded max_steps=6",
            model_calls=6,
            tool_calls=5,
            usage=ModelUsage(input_tokens=120, output_tokens=30),
            latency_ms=42.0,
            steps=("get_service_metrics", "get_dependencies"),
        )

    records = run_benchmark(
        config=_config(),
        patterns=(AutonomyPattern.AGENT,),
        run_pattern=exceed,
        evaluate_run=_grounding,
        evaluate_epistemic_run=_epistemic,
    )
    (summary,) = summarize_benchmark(records, patterns=(AutonomyPattern.AGENT,))

    assert summary.completed == 0
    assert summary.bound_exceeded == 1
    assert summary.bound_exceeded_rate == 1.0
    assert summary.epistemic_evaluated == 0
