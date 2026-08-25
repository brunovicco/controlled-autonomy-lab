"""Utilities for comparing repeated architecture-pattern executions."""

from dataclasses import dataclass
from typing import Protocol

from harness_example.domain.autonomy import AutonomyPattern, PatternRun


class PatternRunner(Protocol):
    """Common runner contract shared by every demonstration pattern."""

    def run(self, incident_id: str) -> PatternRun:
        """Execute one pattern for an incident."""
        ...


@dataclass(frozen=True, slots=True)
class RepetitionSummary:
    """Aggregate trajectory information from repeated executions."""

    pattern: AutonomyPattern
    runs: int
    unique_trajectories: int
    trajectories: tuple[tuple[str, ...], ...]


def repeat_pattern(
    runner: PatternRunner,
    *,
    incident_id: str,
    runs: int,
) -> tuple[PatternRun, ...]:
    """Execute the same architecture multiple times for variance inspection."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    return tuple(runner.run(incident_id) for _ in range(runs))


def summarize_repetitions(results: tuple[PatternRun, ...]) -> RepetitionSummary:
    """Count distinct control-flow trajectories without inspecting answer content."""
    if not results:
        raise ValueError("at least one result is required")
    pattern = results[0].pattern
    if any(result.pattern is not pattern for result in results):
        raise ValueError("all repetition results must use the same pattern")
    trajectories = tuple(result.steps for result in results)
    return RepetitionSummary(
        pattern=pattern,
        runs=len(results),
        unique_trajectories=len(set(trajectories)),
        trajectories=trajectories,
    )
