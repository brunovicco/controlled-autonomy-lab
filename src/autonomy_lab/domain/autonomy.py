"""Domain types for the controlled-autonomy incident-analysis lab."""

from dataclasses import dataclass, field
from enum import StrEnum


class AutonomyPattern(StrEnum):
    """Supported execution patterns ordered by increasing model autonomy."""

    AUGMENTED = "augmented"
    CHAINING = "chaining"
    ROUTING = "routing"
    PARALLEL = "parallel"
    EVALUATOR_OPTIMIZER = "evaluator-optimizer"
    AGENT = "agent"


class IncidentCategory(StrEnum):
    """Bounded routing categories for incident analysis."""

    DEPLOYMENT = "deployment"
    PERFORMANCE = "performance"
    DEPENDENCY = "dependency"
    SECURITY = "security"


@dataclass(frozen=True, slots=True)
class Incident:
    """A production incident presented to every architecture pattern."""

    incident_id: str
    service: str
    started_at: str
    symptom: str


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One bounded piece of evidence available to an analysis."""

    source: str
    summary: str


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Token accounting reported by a model call."""

    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "ModelUsage") -> "ModelUsage":
        """Combine usage from independent calls."""
        return ModelUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass(frozen=True, slots=True)
class ModelTurn:
    """Text returned by one bounded model call."""

    text: str
    usage: ModelUsage = field(default_factory=ModelUsage)
    stop_reason: str = "end_turn"


@dataclass(frozen=True, slots=True)
class PatternRun:
    """Observable result produced by one architecture pattern."""

    pattern: AutonomyPattern
    incident_id: str
    answer: str
    model_calls: int
    tool_calls: int
    steps: tuple[str, ...]
    usage: ModelUsage
    latency_ms: float
