import pytest

from harness_example.adapters.incidents import InMemoryIncidentStore
from harness_example.application.patterns.agent import (
    AgentLimitError,
    BoundedIncidentAgent,
    ToolInputError,
    ToolNotAllowedError,
)
from harness_example.domain.agent import AgentMessage, AgentTurn, ToolCall, ToolSpec
from harness_example.domain.autonomy import AutonomyPattern, ModelUsage


class ScriptedAgentModel:
    def __init__(self, turns: list[AgentTurn]) -> None:
        self._turns = iter(turns)
        self.histories: list[tuple[AgentMessage, ...]] = []

    def next_turn(
        self,
        *,
        system: str,
        messages: tuple[AgentMessage, ...],
        tools: tuple[ToolSpec, ...],
    ) -> AgentTurn:
        assert "read-only" in system
        assert len(tools) == 5
        self.histories.append(messages)
        return next(self._turns)


def _tool_turn(call_id: str, name: str, incident_id: str = "INC-001") -> AgentTurn:
    return AgentTurn(
        message=AgentMessage(
            role="assistant",
            tool_calls=(
                ToolCall(call_id=call_id, name=name, arguments={"incident_id": incident_id}),
            ),
        ),
        usage=ModelUsage(10, 2),
        stop_reason="tool_use",
    )


def _final_turn(
    text: str = "Deployment is a strong hypothesis; verify upstream timeout evidence.",
) -> AgentTurn:
    return AgentTurn(
        message=AgentMessage(role="assistant", text=text),
        usage=ModelUsage(10, 4),
    )


def test_agent_controls_its_trajectory_inside_bounded_tools() -> None:
    model = ScriptedAgentModel(
        [
            _tool_turn("call-1", "get_service_metrics"),
            _tool_turn("call-2", "get_recent_deployments"),
            _final_turn(),
        ]
    )

    result = BoundedIncidentAgent(store=InMemoryIncidentStore(), model=model).run("INC-001")

    assert result.pattern is AutonomyPattern.AGENT
    assert result.model_calls == 3
    assert result.tool_calls == 2
    assert result.steps == (
        "get_service_metrics",
        "get_recent_deployments",
        "final-answer",
    )
    assert result.usage == ModelUsage(30, 8)
    assert model.histories[1][-1].role == "tool"


def test_agent_denies_unlisted_tool() -> None:
    model = ScriptedAgentModel([_tool_turn("call-1", "restart_service")])

    with pytest.raises(ToolNotAllowedError):
        BoundedIncidentAgent(store=InMemoryIncidentStore(), model=model).run("INC-001")


def test_agent_denies_cross_incident_tool_access() -> None:
    model = ScriptedAgentModel([_tool_turn("call-1", "get_service_metrics", "INC-999")])

    with pytest.raises(ToolInputError, match="active incident"):
        BoundedIncidentAgent(store=InMemoryIncidentStore(), model=model).run("INC-001")


def test_agent_stops_when_step_budget_is_exhausted() -> None:
    model = ScriptedAgentModel(
        [
            _tool_turn("call-1", "get_service_metrics"),
            _tool_turn("call-2", "get_dependencies"),
        ]
    )

    with pytest.raises(AgentLimitError, match="max_steps=2"):
        BoundedIncidentAgent(
            store=InMemoryIncidentStore(), model=model, max_steps=2
        ).run("INC-001")
