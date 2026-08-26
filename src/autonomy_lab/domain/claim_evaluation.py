"""Domain contracts for claim-level evaluation v2."""

from dataclasses import dataclass
from enum import StrEnum


class ClaimKind(StrEnum):
    """Mutually exclusive v2 classifications for one evaluable claim."""

    SUPPORTED_FACT = "supported-fact"
    SUPPORTED_INFERENCE = "supported-inference"
    PROPOSED_ACTION = "proposed-action"
    UNSUPPORTED_CLAIM = "unsupported-claim"


@dataclass(frozen=True, slots=True)
class ClaimEvaluation:
    """Classification and bounded evidence metadata for one extracted claim."""

    claim: str
    kind: ClaimKind
    rationale: str
    evidence_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClaimEvaluationReport:
    """Claim-level evaluation summary for one model answer."""

    claims: tuple[ClaimEvaluation, ...]

    @property
    def supported_fact_count(self) -> int:
        """Return the number of claims classified as directly supported facts."""
        return self._count(ClaimKind.SUPPORTED_FACT)

    @property
    def supported_inference_count(self) -> int:
        """Return the number of qualified, evidence-anchored inferences."""
        return self._count(ClaimKind.SUPPORTED_INFERENCE)

    @property
    def proposed_action_count(self) -> int:
        """Return the number of recommendations or other proposed actions."""
        return self._count(ClaimKind.PROPOSED_ACTION)

    @property
    def unsupported_claim_count(self) -> int:
        """Return the number of claims without sufficient v2 support."""
        return self._count(ClaimKind.UNSUPPORTED_CLAIM)

    @property
    def evaluable_claim_count(self) -> int:
        """Return factual/inferential claims, excluding proposed actions."""
        return len(self.claims) - self.proposed_action_count

    @property
    def supported_claim_count(self) -> int:
        """Return supported facts plus supported inferences."""
        return self.supported_fact_count + self.supported_inference_count

    @property
    def support_ratio(self) -> float:
        """Return supported factual/inferential claims divided by evaluable claims."""
        total = self.evaluable_claim_count
        if total == 0:
            return 1.0
        return self.supported_claim_count / total

    def _count(self, kind: ClaimKind) -> int:
        return sum(claim.kind is kind for claim in self.claims)
