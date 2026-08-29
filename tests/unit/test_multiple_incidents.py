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


def test_inc002_live_timeline_associations_are_supported() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-002")
    evidence = store.get_evidence(incident)
    answer = """| Time | Event |
|---|---|
| 09:05 | Baseline: error rate 0.3%, p95 latency 290ms |
| 09:08 | Deploy of v2.19.1; timeout reduced from 3s to 800ms |
| 09:24 | Rollback of v2.19.1; timeout restored to 3s |
"""

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_specifics == ()


def test_http_status_plural_is_not_parsed_as_seconds() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-003")
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer="payments-api 503s begin climbing during the incident.",
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_specifics == ()


def test_spelled_out_fixture_durations_support_numeric_paraphrases() -> None:
    store = InMemoryIncidentStore()

    inc003 = store.get_incident("INC-003")
    report003 = DeterministicGroundingEvaluator().evaluate(
        answer="No deployment or config change occurred in the 6 hours prior.",
        incident=inc003,
        evidence=store.get_evidence(inc003),
    )
    assert report003.unsupported_specifics == ()

    inc004 = store.get_incident("INC-004")
    report004 = DeterministicGroundingEvaluator().evaluate(
        answer="The last deploy was nearly ~3 hrs before the incident.",
        incident=inc004,
        evidence=store.get_evidence(inc004),
    )
    assert report004.unsupported_specifics == ()


def test_confirmed_cause_meta_references_are_not_overclaims() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-002")
    evidence = store.get_evidence(incident)
    answer = (
        "That's a process gap worth reviewing but doesn't change the technical root cause. "
        "INC-901 is unrelated and irrelevant to this root cause."
    )

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()


def test_methodology_and_reported_confirmation_are_not_overclaims() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-003")
    evidence = store.get_evidence(incident)
    answer = (
        "The runbook describes the standard bar for establishing dependency-caused failure. "
        "I'm treating root cause confirmed as reported by the dependency system, "
        "not independently re-derived from raw logs."
    )

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()


def test_inconclusive_smoke_language_preserves_abstention() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-004")
    evidence = store.get_evidence(incident)
    answer = (
        "No single confirmed root cause yet. "
        "No causal conclusion should be drawn yet before attributing root cause."
    )

    grounding = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )
    claims = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert grounding.causality_overclaims == ()
    assert grounding.uncertainty_preserved is True
    assert all(item.kind is ClaimKind.SUPPORTED_INFERENCE for item in claims.claims)


def test_claim_extraction_skips_markdown_table_structure_and_hypothesis_label() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-004")
    evidence = store.get_evidence(incident)
    answer = """| Time | Event |
|---|---|
| 11:20 | p95 latency reached 920ms |

Two plausible, unconfirmed hypotheses:
1. The identity-provider may be a partial contributor.
"""

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )
    texts = {item.claim for item in report.claims}

    assert "| Time | Event |" not in texts
    assert "|---|---|" not in texts
    assert "Two plausible, unconfirmed hypotheses:" not in texts
