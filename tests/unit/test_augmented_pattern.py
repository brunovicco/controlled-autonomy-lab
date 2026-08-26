from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.patterns.augmented import AugmentedIncidentAnalysis
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelTurn, ModelUsage


class StubTextModel:
    def __init__(self) -> None:
        self.system = ""
        self.prompt = ""

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        self.system = system
        self.prompt = prompt
        return ModelTurn(
            text="Deployment timing is a strong hypothesis, not a proven cause.",
            usage=ModelUsage(input_tokens=120, output_tokens=24),
        )


def test_augmented_pattern_uses_one_bounded_model_call() -> None:
    model = StubTextModel()
    runner = AugmentedIncidentAnalysis(store=InMemoryIncidentStore(), model=model)

    result = runner.run("INC-001")

    assert result.pattern is AutonomyPattern.AUGMENTED
    assert result.model_calls == 1
    assert result.tool_calls == 0
    assert result.steps == ("load-evidence", "model-analysis")
    assert result.usage == ModelUsage(120, 24)
    assert "correlation" in model.system.lower()
    assert "[deployments]" in model.prompt
    assert "[runbook]" in model.prompt
