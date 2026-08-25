from harness_example.adapters.incidents import IncidentNotFoundError, InMemoryIncidentStore
from harness_example.domain.autonomy import AutonomyPattern, ModelUsage


def test_incident_fixture_is_deterministic() -> None:
    store = InMemoryIncidentStore()

    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)

    assert incident.service == "checkout-api"
    assert incident.symptom == "HTTP 5xx increased from 0.2% to 8.7%"
    assert [item.source for item in evidence] == [
        "metrics",
        "deployments",
        "dependencies",
        "runbook",
        "previous-incidents",
    ]


def test_incident_store_rejects_unknown_identifier() -> None:
    store = InMemoryIncidentStore()

    try:
        store.get_incident("INC-404")
    except IncidentNotFoundError as exc:
        assert exc.args == ("INC-404",)
    else:
        raise AssertionError("unknown incident must fail closed")


def test_model_usage_is_additive() -> None:
    assert ModelUsage(10, 4) + ModelUsage(7, 3) == ModelUsage(17, 7)


def test_patterns_capture_the_full_autonomy_continuum() -> None:
    assert [pattern.value for pattern in AutonomyPattern] == [
        "augmented",
        "chaining",
        "routing",
        "parallel",
        "evaluator-optimizer",
        "agent",
    ]
