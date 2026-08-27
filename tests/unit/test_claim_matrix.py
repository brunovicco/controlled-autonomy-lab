import json

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.labelled_claims import load_labelled_claims_v1
from autonomy_lab.application.claim_matrix import ClaimJudgeMatrixRunner
from autonomy_lab.application.semantic_claim_evaluation import SemanticClaimEvaluatorV21
from autonomy_lab.domain.autonomy import ModelTurn, ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimKind


class StaticSemanticJudge:
    def __init__(self) -> None:
        self.claims: list[str] = []

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        del system
        payload = json.loads(prompt)
        claim = str(payload["claim"])
        self.claims.append(claim)
        if "A prior incident had similar symptoms from an upstream timeout mismatch" in claim:
            body = {
                "verdict": "supported-fact",
                "rationale": "previous-incidents evidence semantically supports the historical claim",
                "evidence_sources": ["previous-incidents"],
            }
        else:
            body = {
                "verdict": "unsupported-claim",
                "rationale": "bounded evidence is insufficient for this claim",
                "evidence_sources": [],
            }
        return ModelTurn(
            text=json.dumps(body),
            usage=ModelUsage(input_tokens=10, output_tokens=5),
        )


def _fixture():
    claim_set = load_labelled_claims_v1()
    store = InMemoryIncidentStore()
    incident = store.get_incident(claim_set.incident_id)
    return claim_set, incident, store.get_evidence(incident)


def _row(report, case_id: str):
    return next(row for row in report.rows if row.case_id == case_id)


def test_deterministic_matrix_surfaces_known_blind_spots() -> None:
    claim_set, incident, evidence = _fixture()

    report = ClaimJudgeMatrixRunner().evaluate(
        claim_set=claim_set,
        incident=incident,
        evidence=evidence,
    )

    assert report.case_count == 18
    assert report.deterministic_correct_count == 15
    assert report.deterministic_accuracy == 15 / 18
    assert report.final_correct_count == 15
    assert report.false_rejection_count == 1
    assert report.false_upgrade_count == 2
    assert report.authority_false_positive_count == 2
    assert report.semantic_evaluated_count == 0

    historical = _row(report, "fact-historical-paraphrase")
    assert historical.expected_kind is ClaimKind.SUPPORTED_FACT
    assert historical.deterministic_kind is ClaimKind.UNSUPPORTED_CLAIM

    relational = _row(report, "unsupported-time-measurement-association")
    assert relational.expected_kind is ClaimKind.UNSUPPORTED_CLAIM
    assert relational.deterministic_kind is ClaimKind.SUPPORTED_FACT

    historical_trap = _row(report, "unsupported-historical-current-cause")
    assert historical_trap.expected_kind is ClaimKind.UNSUPPORTED_CLAIM
    assert historical_trap.deterministic_kind is ClaimKind.SUPPORTED_INFERENCE


def test_semantic_matrix_can_correct_only_eligible_conservative_misses() -> None:
    claim_set, incident, evidence = _fixture()
    judge = StaticSemanticJudge()

    report = ClaimJudgeMatrixRunner(
        semantic=SemanticClaimEvaluatorV21(model=judge)
    ).evaluate(
        claim_set=claim_set,
        incident=incident,
        evidence=evidence,
    )

    assert report.final_correct_count == 16
    assert report.final_accuracy == 16 / 18
    assert report.corrected_count == 1
    assert report.regressed_count == 0
    assert report.false_rejection_count == 0
    assert report.false_upgrade_count == 2
    assert report.authority_false_positive_count == 2
    assert report.semantic_evaluated_count == 3
    assert report.semantic_model_calls == 3
    assert report.semantic_usage == ModelUsage(input_tokens=30, output_tokens=15)

    historical = _row(report, "fact-historical-paraphrase")
    assert historical.semantic_kind is ClaimKind.SUPPORTED_FACT
    assert historical.final_kind is ClaimKind.SUPPORTED_FACT
    assert historical.corrected_by_semantic is True

    unsupported_version = _row(report, "unsupported-version")
    assert unsupported_version.semantic_evaluated is False
    assert unsupported_version.resolution == "deterministic-hard-failure"

    relational = _row(report, "unsupported-time-measurement-association")
    assert relational.semantic_evaluated is False
    assert relational.final_kind is ClaimKind.SUPPORTED_FACT
