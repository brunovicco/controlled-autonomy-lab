from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator


def _fixture():
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    return incident, store.get_evidence(incident)


def test_causal_rejection_language_is_not_an_overclaim() -> None:
    incident, evidence = _fixture()
    answer = """## Recommended reversible next steps
Avoid treating the historical incident as confirmation of the current root cause.
"""

    report = DeterministicGroundingEvaluator().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaims == ()


def test_unqualified_root_cause_statement_remains_fail_closed() -> None:
    incident, evidence = _fixture()

    report = DeterministicGroundingEvaluator().evaluate(
        answer="The deployment is the root cause of the incident.",
        incident=incident,
        evidence=evidence,
    )

    assert report.causality_overclaim_count == 1
