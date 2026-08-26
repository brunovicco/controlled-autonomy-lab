from pathlib import Path

import pytest

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.semantic_claim_evaluation import (
    SemanticClaimEvaluationError,
    SemanticClaimEvaluatorV21,
)
from autonomy_lab.domain.autonomy import EvidenceItem, ModelTurn, ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimEvaluationReport, ClaimKind

_FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "observed" / "openai_gpt_5_6_luna_agent_inc001.txt"
)


class SequentialModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls = 0

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        assert "bounded semantic support classifier" in system
        assert '"evidence"' in prompt
        self.calls += 1
        return ModelTurn(next(self._responses), ModelUsage(20, 5))


def _fixture_report(
    answer: str,
) -> tuple[ClaimEvaluationReport, tuple[EvidenceItem, ...]]:
    store = InMemoryIncidentStore()
    incident = store.get_incident("INC-001")
    evidence = store.get_evidence(incident)
    deterministic = DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=evidence,
    )
    return deterministic, evidence


def test_semantic_layer_upgrades_only_conservative_historical_paraphrase() -> None:
    deterministic, evidence = _fixture_report(_FIXTURE.read_text(encoding="utf-8"))
    model = SequentialModel(
        [
            (
                '{"verdict":"supported-fact","rationale":"Historical evidence states '
                'the same prior-incident relationship.","evidence_sources":'
                '["previous-incidents"]}'
            )
        ]
    )

    report = SemanticClaimEvaluatorV21(model=model).evaluate(
        deterministic=deterministic,
        evidence=evidence,
    )

    assert model.calls == 1
    assert report.semantic_model_calls == 1
    assert report.semantic_usage == ModelUsage(20, 5)
    assert report.supported_fact_count == 5
    assert report.supported_inference_count == 4
    assert report.proposed_action_count == 4
    assert report.unsupported_claim_count == 0
    assert report.disagreement_count == 1
    assert report.support_ratio == 1.0

    upgraded = next(item for item in report.claims if item.disagreement)
    assert upgraded.deterministic.kind is ClaimKind.UNSUPPORTED_CLAIM
    assert upgraded.semantic is not None
    assert upgraded.semantic.verdict.value == "supported-fact"
    assert upgraded.semantic.evidence_sources == ("previous-incidents",)
    assert upgraded.final_kind is ClaimKind.SUPPORTED_FACT
    assert upgraded.resolution == "semantic-upgrade"


def test_grounding_hard_failure_is_never_sent_to_semantic_model() -> None:
    deterministic, evidence = _fixture_report(
        "v2.18.3 was the release immediately before the incident."
    )
    model = SequentialModel([])

    report = SemanticClaimEvaluatorV21(model=model).evaluate(
        deterministic=deterministic,
        evidence=evidence,
    )

    assert model.calls == 0
    assert report.semantic_model_calls == 0
    assert report.claims[0].semantic is None
    assert report.claims[0].final_kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].resolution == "deterministic-hard-failure"
    assert report.disagreement_count == 0


def test_semantic_unsupported_confirms_conservative_deterministic_result() -> None:
    deterministic, evidence = _fixture_report("The database was saturated.")
    model = SequentialModel(
        [
            (
                '{"verdict":"unsupported-claim","rationale":"No supplied evidence '
                'mentions database saturation.","evidence_sources":[]}'
            )
        ]
    )

    report = SemanticClaimEvaluatorV21(model=model).evaluate(
        deterministic=deterministic,
        evidence=evidence,
    )

    merged = report.claims[0]
    assert merged.semantic is not None
    assert merged.final_kind is ClaimKind.UNSUPPORTED_CLAIM
    assert merged.disagreement is False
    assert merged.resolution == "semantic-confirmed-unsupported"


def test_semantic_response_rejects_unknown_evidence_source() -> None:
    deterministic, evidence = _fixture_report("The database was saturated.")
    model = SequentialModel(
        [
            (
                '{"verdict":"supported-fact","rationale":"Claim is supported.",'
                '"evidence_sources":["external-web"]}'
            )
        ]
    )

    with pytest.raises(SemanticClaimEvaluationError, match="unknown evidence source"):
        SemanticClaimEvaluatorV21(model=model).evaluate(
            deterministic=deterministic,
            evidence=evidence,
        )


def test_semantic_response_requires_exact_json_contract() -> None:
    deterministic, evidence = _fixture_report("The database was saturated.")
    model = SequentialModel(["```json\n{}\n```"])

    with pytest.raises(SemanticClaimEvaluationError, match="invalid JSON"):
        SemanticClaimEvaluatorV21(model=model).evaluate(
            deterministic=deterministic,
            evidence=evidence,
        )
