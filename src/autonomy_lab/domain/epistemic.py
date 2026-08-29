"""Domain types for posture-aware epistemic evaluation."""

from dataclasses import dataclass
from enum import StrEnum


class EvidencePosture(StrEnum):
    """Causal authority granted by the bounded incident evidence."""

    CORRELATIONAL = "correlational"
    CONFIRMED_CAUSE = "confirmed-cause"
    INCONCLUSIVE = "inconclusive"


class EpistemicVerdict(StrEnum):
    """Alignment between answer posture and evidence-authorized causal posture."""

    ALIGNED = "aligned"
    OVERCLAIMED = "overclaimed"
    OVER_HEDGED = "over-hedged"
    INSUFFICIENT_ABSTENTION = "insufficient-abstention"
    NO_POSITION = "no-position"


@dataclass(frozen=True, slots=True)
class EpistemicReport:
    """Deterministic posture-aware evaluation for one answer."""

    expected_posture: EvidencePosture
    verdict: EpistemicVerdict
    causal_assertion_detected: bool
    hedged_causal_language_detected: bool
    abstention_detected: bool
    uncertainty_language_detected: bool
    causality_overclaim_count: int

    @property
    def aligned(self) -> bool:
        """Return whether the answer matches the evidence-authorized causal posture."""
        return self.verdict is EpistemicVerdict.ALIGNED
