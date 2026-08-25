import pytest

from harness_example.adapters.incidents import InMemoryIncidentStore
from harness_example.application.patterns.evaluator_optimizer import (
    EvaluationLimitError,
    EvaluatorOptimizerIncidentAnalysis,
    InvalidEvaluationError,
)
from harness_example.domain.autonomy import AutonomyPattern, ModelTurn, ModelUsage


class SequentialModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        del system, prompt
        return ModelTurn(next(self._responses), ModelUsage(10, 2))


def test_evaluator_optimizer_revises_until_quality_passes() -> None:
    model = SequentialModel(
        [
            "first draft",
            '{"passed": false, "feedback": ["mark deployment as hypothesis"]}',
            "revised grounded draft",
            '{"passed": true, "feedback": []}',
        ]
    )

    result = EvaluatorOptimizerIncidentAnalysis(
        store=InMemoryIncidentStore(), model=model, max_revisions=2
    ).run("INC-001")

    assert result.pattern is AutonomyPattern.EVALUATOR_OPTIMIZER
    assert result.answer == "revised grounded draft"
    assert result.model_calls == 4
    assert result.steps == (
        "generate",
        "evaluate:1",
        "revise:1",
        "evaluate:2",
        "quality-pass",
    )
    assert result.usage == ModelUsage(40, 8)


def test_evaluator_optimizer_rejects_invalid_schema() -> None:
    model = SequentialModel(["draft", "not-json"])

    with pytest.raises(InvalidEvaluationError, match="valid JSON"):
        EvaluatorOptimizerIncidentAnalysis(store=InMemoryIncidentStore(), model=model).run(
            "INC-001"
        )


def test_evaluator_optimizer_stops_at_revision_limit() -> None:
    model = SequentialModel(
        [
            "draft",
            '{"passed": false, "feedback": ["fix grounding"]}',
            "revision",
            '{"passed": false, "feedback": ["still unsupported"]}',
        ]
    )

    with pytest.raises(EvaluationLimitError, match="after 1 revision"):
        EvaluatorOptimizerIncidentAnalysis(
            store=InMemoryIncidentStore(), model=model, max_revisions=1
        ).run("INC-001")
