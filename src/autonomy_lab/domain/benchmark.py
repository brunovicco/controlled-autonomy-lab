"""Domain contracts for reproducible architecture benchmarks."""

from dataclasses import dataclass
from enum import StrEnum

from autonomy_lab.domain.autonomy import AutonomyPattern


class BenchmarkStatus(StrEnum):
    """Outcome of one pattern execution inside a benchmark."""

    OK = "ok"
    RATE_LIMITED = "rate_limited"
    PROVIDER_ERROR = "provider_error"
    BOUND_EXCEEDED = "bound_exceeded"


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Reproducibility metadata shared by every benchmark record."""

    incident_id: str
    runs: int
    provider: str
    model: str
    max_tokens: int
    timeout_seconds: float
    run_interval_seconds: float
    git_commit: str
    reasoning_effort: str | None = None

    def __post_init__(self) -> None:
        """Reject invalid benchmark settings before any provider calls."""
        if self.runs <= 0:
            raise ValueError("runs must be positive")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.run_interval_seconds < 0:
            raise ValueError("run_interval_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    """Metadata-only evidence for one attempted pattern execution."""

    timestamp_utc: str
    git_commit: str
    provider: str
    model: str
    max_tokens: int
    timeout_seconds: float
    reasoning_effort: str | None
    run_interval_seconds: float
    incident_id: str
    pattern: AutonomyPattern
    run_number: int
    status: BenchmarkStatus
    model_calls: int | None = None
    tool_calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    unsupported_count: int | None = None
    proposed_count: int | None = None
    causality_overclaims: int | None = None
    grounding_ratio: float | None = None
    uncertainty_preserved: bool | None = None
    trajectory: tuple[str, ...] = ()
    retry_after: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PatternBenchmarkSummary:
    """Aggregate benchmark metrics for one architecture pattern."""

    pattern: AutonomyPattern
    attempted: int
    completed: int
    rate_limited: int
    provider_errors: int
    completion_rate: float
    rate_limit_rate: float
    provider_error_rate: float
    mean_model_calls: float | None
    mean_tool_calls: float | None
    mean_input_tokens: float | None
    mean_output_tokens: float | None
    mean_total_tokens: float | None
    p50_latency_ms: float | None
    mean_unsupported: float | None
    mean_proposed: float | None
    mean_causality_overclaims: float | None
    mean_grounding_ratio: float | None
    uncertainty_preservation_rate: float | None
    unique_trajectories: int
