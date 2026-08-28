import pytest

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.claim_evaluation import ClaimKind

_REQUIRED_SOURCES = {
    "metrics",
    "deployments",
    "dependencies",
    "runbook",
    "previous-incidents",
}


@pytest.mark.parametrize("incident_id", ["INC-001", "INC-002", "INC-003", "INC-004"])
def test_incident_fixtures_keep_the_same_evidence_boundary(incident_id: str) -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    evidence = store.get_evidence(incident)

    assert incident.incident_id == incident_id
    assert len(evidence) == 5
    assert {item.source for item in evidence} == _REQUIRED_SOURCES


@pytest.mark.parametrize(
    ("incident_id", "answer"),
    [
        (
            "INC-002",
            "The v2.19.1 800ms timeout regression caused the checkout errors.",
        ),
        (
            "INC-003",
            "The payment-provider regional outage caused the downstream 503 errors.",
        ),
    ],
)
def test_explicitly_confirmed_current_causes_are_not_overclaims(
    incident_id: str,
    answer: str,
) -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()


@pytest.mark.parametrize(
    ("incident_id", "answer"),
    [
        ("INC-002", "The payment-provider outage caused INC-002."),
        ("INC-003", "A payments-api deployment caused INC-003."),
        ("INC-004", "The identity-provider latency caused INC-004."),
    ],
)
def test_unconfirmed_or_contradicted_causes_remain_fail_closed(
    incident_id: str,
    answer: str,
) -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaim_count == 1


def test_inconclusive_incident_preserves_abstention() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-004")
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer="Root cause remains unconfirmed for INC-004; more evidence is needed.",
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()
    assert report.uncertainty_preserved is True


@pytest.mark.parametrize(
    ("incident_id", "answer"),
    [
        (
            "INC-002",
            "The v2.19.1 800ms timeout regression caused the checkout errors.",
        ),
        (
            "INC-003",
            "The payment-provider regional outage caused the downstream 503 errors.",
        ),
    ],
)
def test_claim_evaluator_accepts_canonical_confirmed_causes(
    incident_id: str,
    answer: str,
) -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    evidence = store.get_evidence(incident)

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_FACT


def test_original_correlation_fixture_remains_inconclusive() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer="The v2.18.4 deployment caused INC-001.",
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaim_count == 1
