"""Domain types for deterministic grounding evaluation."""

from dataclasses import dataclass
from enum import StrEnum


class GroundingFindingKind(StrEnum):
    """Kinds of deterministic grounding findings surfaced by the lab."""

    UNSUPPORTED_MEASUREMENT = "unsupported-measurement"
    UNSUPPORTED_TIME = "unsupported-time"
    UNSUPPORTED_VERSION = "unsupported-version"
    PROPOSED_PARAMETER = "proposed-parameter"
    CAUSALITY_OVERCLAIM = "causality-overclaim"


@dataclass(frozen=True, slots=True)
class GroundingFinding:
    """One specific grounding finding in a model answer."""

    kind: GroundingFindingKind
    value: str
    context: str


@dataclass(frozen=True, slots=True)
class GroundingReport:
    """Deterministic grounding summary for one pattern answer."""

    supported_specifics: tuple[str, ...]
    unsupported_specifics: tuple[GroundingFinding, ...]
    causality_overclaims: tuple[GroundingFinding, ...]
    uncertainty_preserved: bool
    proposed_specifics: tuple[GroundingFinding, ...] = ()

    @property
    def unsupported_count(self) -> int:
        """Return the number of unique unsupported factual specifics."""
        return len(self.unsupported_specifics)

    @property
    def proposed_count(self) -> int:
        """Return the number of ungrounded parameters used only in proposed actions."""
        return len(self.proposed_specifics)

    @property
    def causality_overclaim_count(self) -> int:
        """Return the number of unqualified strong-causality statements."""
        return len(self.causality_overclaims)

    @property
    def specific_grounding_ratio(self) -> float:
        """Return the share of checked factual specifics grounded in the fixture."""
        total = len(self.supported_specifics) + len(self.unsupported_specifics)
        if total == 0:
            return 1.0
        return len(self.supported_specifics) / total
