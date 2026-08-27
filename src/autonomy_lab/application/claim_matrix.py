"""Run deterministic and optional semantic evaluation over a human-labelled claim set."""

from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.semantic_claim_evaluation import SemanticClaimEvaluatorV21
from autonomy_lab.domain.autonomy import EvidenceItem, Incident, ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimEvaluationReport
from autonomy_lab.domain.claim_matrix import ClaimMatrixReport, ClaimMatrixRow, LabelledClaimSet


class ClaimMatrixError(ValueError):
    """Raised when a labelled case cannot be evaluated as exactly one claim."""


class ClaimJudgeMatrixRunner:
    """Compare deterministic and optional semantic predictions with human labels."""

    def __init__(
        self,
        *,
        deterministic: DeterministicClaimEvaluatorV2 | None = None,
        semantic: SemanticClaimEvaluatorV21 | None = None,
    ) -> None:
        """Configure deterministic authority and optional semantic judge."""
        self._deterministic = deterministic or DeterministicClaimEvaluatorV2()
        self._semantic = semantic

    def evaluate(
        self,
        *,
        claim_set: LabelledClaimSet,
        incident: Incident,
        evidence: tuple[EvidenceItem, ...],
    ) -> ClaimMatrixReport:
        """Evaluate each labelled case independently and aggregate exact-label metrics."""
        if claim_set.incident_id != incident.incident_id:
            raise ClaimMatrixError(
                f"claim set incident {claim_set.incident_id} does not match {incident.incident_id}"
            )

        rows: list[ClaimMatrixRow] = []
        semantic_calls = 0
        semantic_usage = ModelUsage()

        for case in claim_set.cases:
            deterministic_report = self._deterministic.evaluate(
                answer=case.answer,
                incident=incident,
                evidence=evidence,
            )
            if len(deterministic_report.claims) != 1:
                raise ClaimMatrixError(
                    f"claim case {case.case_id} extracted {len(deterministic_report.claims)} claims; expected 1"
                )
            deterministic_claim = deterministic_report.claims[0]

            if self._semantic is None:
                rows.append(
                    ClaimMatrixRow(
                        case_id=case.case_id,
                        category=case.category,
                        claim=deterministic_claim.claim,
                        expected_kind=case.expected_kind,
                        deterministic_kind=deterministic_claim.kind,
                        deterministic_rationale=deterministic_claim.rationale,
                        deterministic_evidence_sources=deterministic_claim.evidence_sources,
                        semantic_kind=None,
                        semantic_rationale=None,
                        semantic_evidence_sources=(),
                        final_kind=deterministic_claim.kind,
                        semantic_evaluated=False,
                        disagreement=False,
                        resolution="deterministic-only",
                    )
                )
                continue

            merged_report = self._semantic.evaluate(
                deterministic=ClaimEvaluationReport(claims=(deterministic_claim,)),
                evidence=evidence,
            )
            if len(merged_report.claims) != 1:
                raise ClaimMatrixError(
                    f"claim case {case.case_id} produced an invalid semantic merge result"
                )
            merged = merged_report.claims[0]
            semantic_calls += merged_report.semantic_model_calls
            semantic_usage += merged_report.semantic_usage
            rows.append(
                ClaimMatrixRow(
                    case_id=case.case_id,
                    category=case.category,
                    claim=deterministic_claim.claim,
                    expected_kind=case.expected_kind,
                    deterministic_kind=deterministic_claim.kind,
                    deterministic_rationale=deterministic_claim.rationale,
                    deterministic_evidence_sources=deterministic_claim.evidence_sources,
                    semantic_kind=(merged.semantic.verdict.claim_kind if merged.semantic else None),
                    semantic_rationale=(merged.semantic.rationale if merged.semantic else None),
                    semantic_evidence_sources=(
                        merged.semantic.evidence_sources if merged.semantic else ()
                    ),
                    final_kind=merged.final_kind,
                    semantic_evaluated=merged.semantic is not None,
                    disagreement=merged.disagreement,
                    resolution=merged.resolution,
                )
            )

        return ClaimMatrixReport(
            claim_set=claim_set,
            rows=tuple(rows),
            semantic_model_calls=semantic_calls,
            semantic_usage=semantic_usage,
        )
