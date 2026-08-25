"""Quality-evaluation domain types for the evaluator-optimizer workflow."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Structured verdict returned by a bounded evaluator step."""

    passed: bool
    feedback: tuple[str, ...]
