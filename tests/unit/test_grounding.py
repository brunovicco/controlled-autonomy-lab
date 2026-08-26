from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.grounding import GroundingFindingKind


def _fixture() -> tuple[Incident, tuple[EvidenceItem, ...]]:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    return incident, store.get_evidence(incident)


def test_supported_specifics_handle_unicode_thousands_and_derived_pp() -> None:
    incident, evidence = _fixture()
    answer = (
        "At 14:10, p95 reached 2\u202f840 ms and the error rate reached 8.7%. "
        "That is an 8.5 pp increase from 0.2%. v2.18.4 was deployed at 13:58. "
        "These events are correlated; causality is not proven."
    )

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_specifics == ()
    assert report.proposed_specifics == ()
    assert report.causality_overclaims == ()
    assert report.uncertainty_preserved is True
    assert {"2840ms", "8.7%", "8.5pp", "0.2%", "v2.18.4", "14:10", "13:58"}.issubset(
        set(report.supported_specifics)
    )
    assert report.specific_grounding_ratio == 1.0


def test_unsupported_specifics_match_observed_live_run_failures() -> None:
    incident, evidence = _fixture()
    answer = (
        "p95 rose through 1\u202f250 ms while provider latency moved from 450 ms to 1,200 ms.\n"
        "Revert to v2.18.3 and restore the timeout to 3 s.\n"
        "Monitor the result for 30\u201360 min."
    )

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    findings = {(finding.kind, finding.value) for finding in report.unsupported_specifics}
    assert (GroundingFindingKind.UNSUPPORTED_MEASUREMENT, "1\u202f250 ms") in findings
    assert (GroundingFindingKind.UNSUPPORTED_MEASUREMENT, "450 ms") in findings
    assert (GroundingFindingKind.UNSUPPORTED_MEASUREMENT, "1,200 ms") in findings
    assert (GroundingFindingKind.UNSUPPORTED_VERSION, "v2.18.3") in findings
    assert (GroundingFindingKind.UNSUPPORTED_MEASUREMENT, "3 s") in findings
    assert (GroundingFindingKind.UNSUPPORTED_MEASUREMENT, "30\u201360 min") in findings
    assert report.unsupported_count == 6


def test_timestamp_text_does_not_create_false_percentage_measurement() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer="Service metrics: 13:55 % 5xx = 0.2 % and 14:10 = 8.7 %.",
        incident=incident,
        evidence=evidence,
    )

    values = {finding.value for finding in report.unsupported_specifics}
    assert "55 %" not in values
    assert report.unsupported_count == 0


def test_recommendation_parameters_are_tracked_separately() -> None:
    incident, evidence = _fixture()
    answer = """## Recommended next steps
Collect logs for 14:00-14:15.
Monitor for 15-30 minutes.
Create an alert above 5% and p95 above 1 s.
"""

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_count == 0
    assert report.proposed_count == 4
    proposed = {finding.value for finding in report.proposed_specifics}
    assert {"14:15", "15-30 minutes", "5%", "1 s"} == proposed
    assert all(
        finding.kind is GroundingFindingKind.PROPOSED_PARAMETER
        for finding in report.proposed_specifics
    )
    assert report.specific_grounding_ratio == 1.0


def test_unknown_timestamp_is_reported() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer="The service recovered at 14:07.",
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_count == 1
    assert report.unsupported_specifics[0].kind is GroundingFindingKind.UNSUPPORTED_TIME
    assert report.unsupported_specifics[0].value == "14:07"


def test_duplicate_unsupported_specific_is_counted_once() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer="Roll back to v2.18.3. The previous version was v2.18.3.",
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_count == 1


def test_unqualified_causality_is_reported() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer="The deployment caused the incident.",
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaim_count == 1
    assert report.causality_overclaims[0].kind is GroundingFindingKind.CAUSALITY_OVERCLAIM
    assert report.uncertainty_preserved is False


def test_qualified_hypothesis_preserves_uncertainty() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer=(
            "Hypothesis: the deployment may have caused the increase, but the timing is only "
            "correlation and causality is not proven."
        ),
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()
    assert report.uncertainty_preserved is True


def test_hypothesis_section_qualifies_causal_language() -> None:
    incident, evidence = _fixture()
    answer = """## Hypotheses (not proven)
1. The new timeout is too low, causing downstream timeouts.
2. The payment provider is the root cause of the spike.
"""

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()
    assert report.uncertainty_preserved is True
