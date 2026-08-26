"""Domain contracts for secondary semantic claim evaluation v2.1."""

from dataclasses import dataclass, field
from enum import StrEnum

from autonomy_lab.domain.autonomy import ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimEvaluation, ClaimKind


class SemanticClaimVerdict(StrEnum):
    """Allowed semantic verdicts for one non-action claim."""

    SUPPORTED_FACT = "supported-fact"
    SUPPORTED_INFERENCE = "supported-inference"
    UNSUPPORTED_CLAIM = "unsupported-claim"

    @property
    def claim_kind(self) -> ClaimKind:
        """Map the semantic verdict to the shared claim taxonomy."""
        return ClaimKind(self.value)


@dataclass(frozen=True, slots=True)
class SemanticClaimJudgement:
    """One bounded semantic judgement produced from fixture evidence only."""

    claim: str
    verdict: SemanticClaimVerdict
    rationale: str
    evidence_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MergedClaimEvaluation:
    """Deterministic and optional semantic outcomes plus the authoritative result."""

    deterministic: ClaimEvaluation
    semantic: SemanticClaimJudgement | None
    final_kind: ClaimKind
    disagreement: bool
    resolution: str


@dataclass(frozen=True, slots=True)
class MergedClaimEvaluationReport:
    """Merged v2.1 report with semantic-call accounting kept separate from the pattern run."""

    claims: tuple[MergedClaimEvaluation, ...]
    semantic_model_calls: int = 0
    semantic_usage: ModelUsage = field(default_factory=ModelUsage)

    @property
    def supported_fact_count(self) -> int:
        return self._count(ClaimKind.SUPPORTED_FACT)

    @property
    def supported_inference_count(self) -> int:
        return self._count(ClaimKind.SUPPORTED_INFERENCE)

    @property
    def proposed_action_count(self) -> int:
        return self._count(ClaimKind.PROPOSED_ACTION)

    @property
    def unsupported_claim_count(self) -> int:
        return self._count(ClaimKind.UNSUPPORTED_CLAIM)

    @property
    def disagreement_count(self) -> int:
        return sum(item.disagreement for item in self.claims)

    @property
    def evaluable_claim_count(self) -> int:
        return len(self.claims) - self.proposed_action_count

    @property
    def supported_claim_count(self) -> int:
        return self.supported_fact_count + self.supported_inference_count

    @property
    def support_ratio(self) -> float:
        total = self.evaluable_claim_count
        if total == 0:
            return 1.0
        return self.supported_claim_count / total

    def _count(self, kind: ClaimKind) -> int:
        return sum(item.final_kind is kind for item in self.claims)
