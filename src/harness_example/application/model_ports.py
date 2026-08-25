"""Combined provider-neutral model port used by CLI composition."""

from typing import Protocol

from harness_example.application.agent_ports import AgentModel
from harness_example.application.ports import TextModel


class ModelClient(TextModel, AgentModel, Protocol):
    """Model boundary supporting text completion and bounded tool-use turns."""

    pass
