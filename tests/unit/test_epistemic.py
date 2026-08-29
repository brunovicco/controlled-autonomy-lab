from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.epistemic import (
    DeterministicEpistemicEvaluator,
    infer_evidence_posture,
)
from autonomy_lab.domain.epistemic import EpistemicVerdict, EvidencePosture


def _fixture(incident_id: str):
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    return incident, store.get_evidence(incident)


def _evaluate(incident_id: str, answer: str):
    incident, evidence = _fixture(incident_id)
    return DeterministicEpistemicEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )


def test_fixture_postures_are_inferred_from_evidence() -> None:
    expected = {
        "INC-001": EvidencePosture.CORRELATIONAL,
        "INC-002": EvidencePosture.CONFIRMED_CAUSE,
        "INC-003": EvidencePosture.CONFIRMED_CAUSE,
        "INC-004": EvidencePosture.INCONCLUSIVE,
    }

    for incident_id, posture in expected.items():
        incident, evidence = _fixture(incident_id)
        assert infer_evidence_posture(incident=incident, evidence=evidence) is posture


def test_correlation_fixture_accepts_qualified_hypothesis() -> None:
    report = _evaluate(
        "INC-001",
        "The deployment may have contributed, but causality is not proven.",
    )

    assert report.verdict is EpistemicVerdict.ALIGNED
    assert report.aligned is True
    assert report.hedged_causal_language_detected is True
    assert report.uncertainty_language_detected is True


def test_correlation_fixture_rejects_unqualified_causal_claim() -> None:
    report = _evaluate("INC-001", "The deployment caused the incident.")

    assert report.verdict is EpistemicVerdict.OVERCLAIMED
    assert report.aligned is False
    assert report.causality_overclaim_count == 1


def test_confirmed_deployment_fixture_accepts_direct_causal_statement() -> None:
    report = _evaluate(
        "INC-002",
        "The v2.19.1 800ms timeout regression caused the checkout errors.",
    )

    assert report.verdict is EpistemicVerdict.ALIGNED
    assert report.causal_assertion_detected is True
    assert report.causality_overclaim_count == 0


def test_confirmed_dependency_fixture_accepts_direct_causal_statement() -> None:
    report = _evaluate(
        "INC-003",
        "The payment-provider regional outage caused the downstream 503 errors.",
    )

    assert report.verdict is EpistemicVerdict.ALIGNED
    assert report.causal_assertion_detected is True
    assert report.causality_overclaim_count == 0


def test_confirmed_fixture_flags_unnecessary_hedging() -> None:
    report = _evaluate(
        "INC-002",
        "The v2.19.1 timeout regression may have caused the checkout errors.",
    )

    assert report.verdict is EpistemicVerdict.OVER_HEDGED
    assert report.uncertainty_language_detected is True
    assert report.hedged_causal_language_detected is True


def test_inconclusive_fixture_requires_explicit_abstention() -> None:
    report = _evaluate(
        "INC-004",
        "Root cause remains unconfirmed; there is insufficient evidence to attribute a cause.",
    )

    assert report.verdict is EpistemicVerdict.ALIGNED
    assert report.abstention_detected is True
    assert report.uncertainty_language_detected is True


def test_inconclusive_fixture_rejects_hedging_as_substitute_for_abstention() -> None:
    report = _evaluate(
        "INC-004",
        "The identity-provider latency likely caused the incident.",
    )

    assert report.uncertainty_language_detected is True
    assert report.hedged_causal_language_detected is True
    assert report.abstention_detected is False
    assert report.verdict is EpistemicVerdict.INSUFFICIENT_ABSTENTION
    assert report.aligned is False


def test_inconclusive_fixture_rejects_strong_causal_claim() -> None:
    report = _evaluate(
        "INC-004",
        "The identity-provider latency caused the profile-api incident.",
    )

    assert report.verdict is EpistemicVerdict.OVERCLAIMED


def test_no_causal_position_is_distinct_from_aligned_uncertainty() -> None:
    report = _evaluate(
        "INC-001",
        "HTTP 5xx reached 8.7% and p95 reached 2840ms.",
    )

    assert report.verdict is EpistemicVerdict.NO_POSITION
    assert report.uncertainty_language_detected is False


def test_historical_causal_statement_does_not_define_current_posture() -> None:
    report = _evaluate(
        "INC-001",
        "Historical context: INC-884 was caused by an upstream timeout mismatch. "
        "For INC-001, causality is not proven.",
    )

    assert report.verdict is EpistemicVerdict.ALIGNED
    assert report.causal_assertion_detected is False
    assert report.abstention_detected is True
