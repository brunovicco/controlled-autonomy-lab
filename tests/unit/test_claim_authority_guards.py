from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_authority_guards import (
    has_unsupported_explicit_time_measurement_association,
    promotes_historical_context_to_current_causality,
)
from autonomy_lab.domain.autonomy import EvidenceItem, Incident


def _fixture() -> tuple[Incident, tuple[EvidenceItem, ...]]:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    return incident, store.get_evidence(incident)


def test_false_prose_time_measurement_association_is_rejected() -> None:
    _, evidence = _fixture()

    assert has_unsupported_explicit_time_measurement_association(
        "At 14:05, p95 latency was 2,840 ms.",
        evidence=evidence,
    )


def test_supported_prose_time_measurement_association_is_preserved() -> None:
    _, evidence = _fixture()

    assert not has_unsupported_explicit_time_measurement_association(
        "At 14:10, p95 latency was 2,840 ms.",
        evidence=evidence,
    )


def test_multi_pair_observation_is_not_overinterpreted_by_narrow_guard() -> None:
    _, evidence = _fixture()

    assert not has_unsupported_explicit_time_measurement_association(
        "HTTP 5xx increased from 0.2% at 13:55 to 8.7% at 14:10.",
        evidence=evidence,
    )


def test_historical_context_cannot_establish_current_incident_cause() -> None:
    incident, evidence = _fixture()

    assert promotes_historical_context_to_current_causality(
        "INC-884 proves the current incident was caused by an upstream timeout mismatch.",
        incident=incident,
        evidence=evidence,
    )


def test_historical_cause_remains_valid_when_current_cause_is_not_asserted() -> None:
    incident, evidence = _fixture()

    assert not promotes_historical_context_to_current_causality(
        "INC-884 had similar symptoms caused by an upstream timeout mismatch; "
        "the current incident remains unconfirmed.",
        incident=incident,
        evidence=evidence,
    )


def test_explicit_rejection_of_historical_current_causality_is_preserved() -> None:
    incident, evidence = _fixture()

    assert not promotes_historical_context_to_current_causality(
        "INC-884 does not prove the current incident was caused by an upstream timeout mismatch.",
        incident=incident,
        evidence=evidence,
    )
