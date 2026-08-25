"""Provider-neutral domain types for bounded tool-using agents."""

from dataclasses import dataclass, field
from typing import Literal, Mapping

from harness_example.domain.autonomy import ModelUsage


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A narrow client tool contract exposed to a model."""

    name: str
    description: str
    input_schema: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One model-requested client tool invocation."""

    call_id: str
    name: str
    arguments: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Result returned to the model for one client tool call."""

    call_id: str
    content: str
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class AgentMessage:
    """Provider-neutral conversation message used by the agent loop."""

    role: Literal["user", "assistant", "tool"]
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    tool_results: tuple[ToolResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AgentTurn:
    """One model turn that may contain text, tool calls, or both."""

    message: AgentMessage
    usage: ModelUsage = field(default_factory=ModelUsage)
    stop_reason: str = "end_turn"
