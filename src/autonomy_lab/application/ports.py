"""Application ports used by architecture-pattern implementations."""

from typing import Protocol

from autonomy_lab.domain.autonomy import EvidenceItem, Incident, ModelTurn


class TextModel(Protocol):
    """Port for one bounded text-generation call."""

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        """Generate one model turn for a system instruction and prompt."""
        ...


class IncidentStore(Protocol):
    """Read-only evidence boundary for the incident-analysis lab."""

    def get_incident(self, incident_id: str) -> Incident:
        """Return one incident by stable identifier."""
        ...

    def get_evidence(self, incident: Incident) -> tuple[EvidenceItem, ...]:
        """Return bounded evidence associated with an incident."""
        ...
