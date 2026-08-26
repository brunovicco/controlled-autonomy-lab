from pathlib import Path

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.claim_evaluation import ClaimKind

_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "observed"
    / "openai_gpt_5_6_luna_agent_inc001.txt"
)


def _observed_answer() -> str:
    return _FIXTURE.read_text(encoding="utf-8")


def test_observed_agent_answer_has_no_false_causality_overclaim() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)

    report = DeterministicGroundingEvaluator().evaluate(
        answer=_observed_answer(),
        incident=incident,
        evidence=evidence,
    )

    assert report.unsupported_specifics == ()
    assert report.causality_overclaims == ()
    assert report.uncertainty_preserved is True
    assert report.specific_grounding_ratio == 1.0


def test_observed_agent_claim_partition_is_stable() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=_observed_answer(),
        incident=incident,
        evidence=evidence,
    )

    assert len(report.claims) == 13
    assert report.supported_fact_count == 4
    assert report.supported_inference_count == 4
    assert report.proposed_action_count == 4
    assert report.unsupported_claim_count == 1
    assert report.evaluable_claim_count == 9
    assert report.supported_claim_count == 8
    assert report.support_ratio == 8 / 9

    historical = next(
        claim for claim in report.claims if claim.claim.startswith("A prior incident")
    )
    assert historical.kind is ClaimKind.UNSUPPORTED_CLAIM
    assert historical.rationale == "deterministic-v2-no-direct-support"

    conclusion = next(
        claim for claim in report.claims if claim.claim.startswith("No confirmed root cause")
    )
    assert conclusion.kind is ClaimKind.SUPPORTED_INFERENCE
    assert conclusion.rationale == "qualified-inference-with-evidence-anchor"


def test_proposal_heading_does_not_absorb_following_unlisted_conclusion() -> None:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)
    answer = """**Recommended reversible next steps**
1. Continue monitoring 5xx rate.

No confirmed root cause is currently available.
"""

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert [claim.kind for claim in report.claims] == [
        ClaimKind.PROPOSED_ACTION,
        ClaimKind.SUPPORTED_INFERENCE,
    ]
