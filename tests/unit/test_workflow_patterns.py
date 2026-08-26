from threading import Lock

import pytest

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.patterns.chaining import ChainedIncidentAnalysis
from autonomy_lab.application.patterns.parallel import ParallelIncidentAnalysis
from autonomy_lab.application.patterns.routing import InvalidRouteError, RoutedIncidentAnalysis
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelTurn, ModelUsage


class SequentialModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls = 0

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        del system, prompt
        self.calls += 1
        return ModelTurn(next(self._responses), ModelUsage(10, 2))


class PromptAwareParallelModel:
    def __init__(self) -> None:
        self.calls = 0
        self._lock = Lock()

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        del system
        with self._lock:
            self.calls += 1
        if prompt.startswith("Focus: metrics"):
            text = "metrics finding"
        elif prompt.startswith("Focus: changes"):
            text = "changes finding"
        elif prompt.startswith("Focus: dependencies"):
            text = "dependency finding"
        else:
            assert "[metrics]" in prompt
            assert "[changes]" in prompt
            assert "[dependencies]" in prompt
            text = "aggregated finding"
        return ModelTurn(text, ModelUsage(5, 1))


def test_chaining_keeps_a_fixed_three_step_path() -> None:
    model = SequentialModel(["facts", "assessment", "recommendation"])
    result = ChainedIncidentAnalysis(store=InMemoryIncidentStore(), model=model).run("INC-001")

    assert result.pattern is AutonomyPattern.CHAINING
    assert result.steps == ("extract-facts", "assess", "recommend")
    assert result.model_calls == 3
    assert result.usage == ModelUsage(30, 6)
    assert result.answer == "recommendation"


def test_routing_accepts_only_a_bounded_path() -> None:
    model = SequentialModel(["deployment", "deployment analysis"])
    result = RoutedIncidentAnalysis(store=InMemoryIncidentStore(), model=model).run("INC-001")

    assert result.pattern is AutonomyPattern.ROUTING
    assert result.steps == ("classify", "route:deployment", "model-analysis")
    assert result.model_calls == 2


def test_routing_fails_closed_for_unknown_model_route() -> None:
    model = SequentialModel(["invented-route"])

    with pytest.raises(InvalidRouteError, match="unsupported route"):
        RoutedIncidentAnalysis(store=InMemoryIncidentStore(), model=model).run("INC-001")


def test_parallelization_fans_out_then_aggregates() -> None:
    model = PromptAwareParallelModel()
    result = ParallelIncidentAnalysis(store=InMemoryIncidentStore(), model=model).run("INC-001")

    assert result.pattern is AutonomyPattern.PARALLEL
    assert result.model_calls == 4
    assert result.tool_calls == 0
    assert result.steps == ("fan-out:3", "fan-in", "aggregate")
    assert result.usage == ModelUsage(20, 4)
    assert result.answer == "aggregated finding"
    assert model.calls == 4
