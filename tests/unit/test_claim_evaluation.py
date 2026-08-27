from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.claim_evaluation import ClaimKind


def _fixture() -> tuple[Incident, tuple[EvidenceItem, ...]]:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    return incident, store.get_evidence(incident)


def test_supported_fact_uses_grounding_v1_hard_signal() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="v2.18.4 was deployed at 13:58.",
        incident=incident,
        evidence=evidence,
    )

    assert len(report.claims) == 1
    claim = report.claims[0]
    assert claim.kind is ClaimKind.SUPPORTED_FACT
    assert claim.rationale == "deterministic-fixture-support"
    assert "deployments" in claim.evidence_sources


def test_exact_fixture_text_without_numeric_specifics_can_be_supported_fact() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="No confirmed outage.",
        incident=incident,
        evidence=evidence,
    )

    assert report.claims[0].kind is ClaimKind.SUPPORTED_FACT
    assert report.support_ratio == 1.0


def test_high_confidence_deployment_paraphrase_can_be_supported_fact() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="The deployment included a new payment-provider timeout configuration.",
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.SUPPORTED_FACT
    assert claim.rationale == "deterministic-fixture-support"
    assert "deployments" in claim.evidence_sources


def test_high_confidence_dependency_negation_can_be_supported_fact() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="There is no confirmed payment-provider outage.",
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.SUPPORTED_FACT
    assert claim.rationale == "deterministic-fixture-support"
    assert "dependencies" in claim.evidence_sources


def test_paraphrase_support_preserves_negation_polarity() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="There is a confirmed payment-provider outage.",
        incident=incident,
        evidence=evidence,
    )

    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].rationale == "deterministic-v2-no-direct-support"


def test_historical_paraphrase_remains_semantic_candidate() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=(
            "A previous incident involved an upstream timeout mismatch, "
            "but that is historical context only."
        ),
        incident=incident,
        evidence=evidence,
    )

    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].rationale == "deterministic-v2-no-direct-support"
    assert report.claims[0].evidence_sources == ("previous-incidents",)


def test_qualified_evidence_anchored_hypothesis_is_supported_inference() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=(
            "The leading hypothesis may involve an interaction between the timeout "
            "configuration and payment-provider latency."
        ),
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.SUPPORTED_INFERENCE
    assert claim.rationale == "qualified-inference-with-evidence-anchor"
    assert claim.evidence_sources


def test_hypothesis_without_evidence_anchor_is_unsupported() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="A memory leak might explain the incident.",
        incident=incident,
        evidence=evidence,
    )

    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].rationale == "inference-without-evidence-anchor"


def test_proposal_context_precedes_grounding_of_new_parameters() -> None:
    incident, evidence = _fixture()
    answer = """## Recommended next steps
Monitor for 15 minutes.
Restore the previous timeout configuration.
"""

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert [claim.kind for claim in report.claims] == [
        ClaimKind.PROPOSED_ACTION,
        ClaimKind.PROPOSED_ACTION,
    ]
    assert report.proposed_action_count == 2
    assert report.evaluable_claim_count == 0
    assert report.support_ratio == 1.0


def test_unsupported_specific_is_fail_closed() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="v2.18.3 was the release immediately before the incident.",
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.UNSUPPORTED_CLAIM
    assert claim.rationale == "grounding-v1-unsupported-specifics:1"


def test_causality_overclaim_is_fail_closed() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="The deployment caused the incident.",
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.UNSUPPORTED_CLAIM
    assert claim.rationale == "grounding-v1-causality-overclaim:1"


def test_explicit_not_prove_causal_language_is_supported_inference() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=(
            "The deployment preceded the error increase, and the dependency became slower shortly "
            "afterward, but the available evidence does not prove that the deployment caused the "
            "incident or that the payment provider is the sole cause."
        ),
        incident=incident,
        evidence=evidence,
    )

    claim = report.claims[0]
    assert claim.kind is ClaimKind.SUPPORTED_INFERENCE
    assert claim.rationale == "qualified-inference-with-evidence-anchor"
    assert "deployments" in claim.evidence_sources
    assert "dependencies" in claim.evidence_sources


def test_unverified_declarative_paraphrase_is_conservative_unsupported() -> None:
    incident, evidence = _fixture()

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer="The database was saturated.",
        incident=incident,
        evidence=evidence,
    )

    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].rationale == "deterministic-v2-no-direct-support"


def test_report_counts_keep_proposals_out_of_support_ratio() -> None:
    incident, evidence = _fixture()
    answer = """## Observed facts
v2.18.4 was deployed at 13:58.
The database was saturated.

## Hypotheses
The timeout configuration may interact with payment-provider latency.

## Actions
Monitor for 15 minutes.
"""

    report = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )

    assert report.supported_fact_count == 1
    assert report.supported_inference_count == 1
    assert report.unsupported_claim_count == 1
    assert report.proposed_action_count == 1
    assert report.evaluable_claim_count == 3
    assert report.supported_claim_count == 2
    assert report.support_ratio == 2 / 3
