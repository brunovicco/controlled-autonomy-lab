from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.grounding import GroundingFindingKind, GroundingReport


def _evaluate(answer: str) -> GroundingReport:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    return DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=store.get_evidence(incident),
    )


def test_equivalent_seconds_are_supported_for_fixture_milliseconds() -> None:
    report = _evaluate("At 14:10, p95 latency reached 2.84 s.")

    assert report.unsupported_specifics == ()
    assert "2840ms" in report.supported_specifics


def test_explicit_rounded_approximation_is_supported() -> None:
    report = _evaluate("Observed p95 latency climbed to ~2.8 s.")

    assert report.unsupported_specifics == ()
    assert "2840ms" in report.supported_specifics


def test_unqualified_rounded_measurement_remains_checkable() -> None:
    report = _evaluate("Observed p95 latency climbed to 2.8 s.")

    assert report.unsupported_count == 1
    assert report.unsupported_specifics[0].kind is GroundingFindingKind.UNSUPPORTED_MEASUREMENT
    assert report.unsupported_specifics[0].value == "2.8 s"


def test_recommendation_parameters_in_bold_section_are_proposed() -> None:
    report = _evaluate(
        """**Recommended next steps (all reversible)**
Monitor for 15-30 minutes.
Create an alert above 5% and p95 above 1 s.
"""
    )

    assert report.unsupported_count == 0
    assert report.proposed_count == 3
    assert {finding.value for finding in report.proposed_specifics} == {
        "15-30 minutes",
        "5%",
        "1 s",
    }


def test_invented_observation_window_endpoint_remains_unsupported() -> None:
    report = _evaluate("Dependency latency increased during the observed interval 14:00-14:15.")

    assert report.unsupported_count == 1
    assert report.unsupported_specifics[0].kind is GroundingFindingKind.UNSUPPORTED_TIME
    assert report.unsupported_specifics[0].value == "14:15"


def test_supported_historical_causality_is_not_an_overclaim() -> None:
    report = _evaluate(
        "Incident INC-884 had a similar pattern; root cause was an upstream timeout mismatch."
    )

    assert report.causality_overclaims == ()


def test_historical_incident_does_not_exempt_an_invented_cause() -> None:
    report = _evaluate("Incident INC-884 root cause was database corruption.")

    assert len(report.causality_overclaims) == 1
    assert report.causality_overclaims[0].value == "root cause"
