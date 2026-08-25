"""Bounded tool-using agent for open-ended incident investigation."""

from time import perf_counter

from harness_example.application.agent_ports import AgentModel
from harness_example.application.ports import IncidentStore
from harness_example.domain.agent import AgentMessage, ToolCall, ToolResult, ToolSpec
from harness_example.domain.autonomy import AutonomyPattern, EvidenceItem, ModelUsage, PatternRun

_TOOL_NAMES = (
    "get_service_metrics",
    "get_recent_deployments",
    "get_dependencies",
    "search_runbook",
    "get_previous_incidents",
)

_SOURCE_BY_TOOL = {
    "get_service_metrics": "metrics",
    "get_recent_deployments": "deployments",
    "get_dependencies": "dependencies",
    "search_runbook": "runbook",
    "get_previous_incidents": "previous-incidents",
}

_TOOL_SPECS = tuple(
    ToolSpec(
        name=name,
        description=(
            "Read one evidence category for the current incident. This tool is read-only and "
            "cannot mutate production systems."
        ),
        input_schema={
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
            "additionalProperties": False,
        },
    )
    for name in _TOOL_NAMES
)

_SYSTEM = """You are a bounded production-incident investigation agent.
Choose among the provided read-only evidence tools based on what you have learned so far. Stop
when enough evidence exists to provide a useful assessment. Distinguish observed facts from
hypotheses, never turn correlation into proven causality, and recommend only reversible next
steps. You cannot restart services, rollback deployments, change configuration, or access a shell.
"""


class AgentLimitError(RuntimeError):
    """Raised when the agent does not finish inside deterministic budgets."""


class ToolNotAllowedError(PermissionError):
    """Raised when the model requests a tool outside the explicit allowlist."""


class ToolInputError(ValueError):
    """Raised when a tool request exceeds the current incident scope."""


class BoundedIncidentAgent:
    """Let the model control investigation order inside narrow deterministic guards."""

    def __init__(
        self,
        *,
        store: IncidentStore,
        model: AgentModel,
        max_steps: int = 6,
        max_tool_calls: int = 8,
    ) -> None:
        """Inject dependencies and finite autonomy budgets."""
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if max_tool_calls <= 0:
            raise ValueError("max_tool_calls must be positive")
        self._store = store
        self._model = model
        self._max_steps = max_steps
        self._max_tool_calls = max_tool_calls

    def run(self, incident_id: str) -> PatternRun:
        """Run the model-controlled trajectory until completion or a hard limit."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        messages: list[AgentMessage] = [
            AgentMessage(
                role="user",
                text=(
                    f"Investigate {incident.incident_id} on {incident.service}. "
                    f"Started {incident.started_at}. Symptom: {incident.symptom}"
                ),
            )
        ]
        usage = ModelUsage()
        tool_calls = 0
        steps: list[str] = []

        for step_number in range(1, self._max_steps + 1):
            turn = self._model.next_turn(
                system=_SYSTEM,
                messages=tuple(messages),
                tools=_TOOL_SPECS,
            )
            usage += turn.usage
            messages.append(turn.message)
            if turn.message.tool_calls:
                results: list[ToolResult] = []
                for call in turn.message.tool_calls:
                    if tool_calls >= self._max_tool_calls:
                        raise AgentLimitError("agent exceeded max_tool_calls")
                    result = self._execute_tool(call, incident_id=incident_id, evidence=evidence)
                    tool_calls += 1
                    steps.append(call.name)
                    results.append(result)
                messages.append(AgentMessage(role="tool", tool_results=tuple(results)))
                continue

            answer = turn.message.text.strip()
            if answer:
                steps.append("final-answer")
                return PatternRun(
                    pattern=AutonomyPattern.AGENT,
                    incident_id=incident.incident_id,
                    answer=answer,
                    model_calls=step_number,
                    tool_calls=tool_calls,
                    steps=tuple(steps),
                    usage=usage,
                    latency_ms=(perf_counter() - started) * 1000,
                )
            raise AgentLimitError("agent returned neither tool calls nor a final answer")

        raise AgentLimitError(f"agent exceeded max_steps={self._max_steps}")

    @staticmethod
    def _execute_tool(
        call: ToolCall,
        *,
        incident_id: str,
        evidence: tuple[EvidenceItem, ...],
    ) -> ToolResult:
        source = _SOURCE_BY_TOOL.get(call.name)
        if source is None:
            raise ToolNotAllowedError(call.name)
        requested_incident = call.arguments.get("incident_id")
        if requested_incident != incident_id:
            raise ToolInputError("tool incident_id must match the active incident")
        item = next((candidate for candidate in evidence if candidate.source == source), None)
        if item is None:
            return ToolResult(call_id=call.call_id, content="No evidence available.")
        return ToolResult(call_id=call.call_id, content=item.summary)
