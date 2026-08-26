"""Application port for provider-neutral tool-using model turns."""

from typing import Protocol

from autonomy_lab.domain.agent import AgentMessage, AgentTurn, ToolSpec


class AgentModel(Protocol):
    """Port allowing a model to choose among a bounded set of client tools."""

    def next_turn(
        self,
        *,
        system: str,
        messages: tuple[AgentMessage, ...],
        tools: tuple[ToolSpec, ...],
    ) -> AgentTurn:
        """Return the model's next text/tool-use turn."""
        ...
