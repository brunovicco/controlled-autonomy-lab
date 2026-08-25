"""Bounded routing workflow for incident analysis."""

from time import perf_counter

from harness_example.application.ports import IncidentStore, TextModel
from harness_example.domain.autonomy import (
    AutonomyPattern,
    EvidenceItem,
    Incident,
    IncidentCategory,
    PatternRun,
)


class InvalidRouteError(ValueError):
    """Raised when a model classifier returns a route outside the allowlist."""


def _render_context(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    evidence_text = "\n".join(f"- [{item.source}] {item.summary}" for item in evidence)
    return (
        f"Incident {incident.incident_id} on {incident.service}: {incident.symptom}\n\n"
        f"Evidence:\n{evidence_text}"
    )


_ROUTE_INSTRUCTIONS = {
    IncidentCategory.DEPLOYMENT: (
        "Focus on release timing, configuration changes, rollback evidence, and alternative causes."
    ),
    IncidentCategory.PERFORMANCE: (
        "Focus on latency, saturation, error-rate movement, and evidence needed to isolate "
        "a bottleneck."
    ),
    IncidentCategory.DEPENDENCY: (
        "Focus on upstream/downstream behavior and distinguish dependency correlation from "
        "confirmed cause."
    ),
    IncidentCategory.SECURITY: (
        "Focus on security-relevant indicators and escalate uncertainty instead of inventing "
        "compromise evidence."
    ),
}


class RoutedIncidentAnalysis:
    """Let the model select one of four code-owned downstream paths."""

    def __init__(self, *, store: IncidentStore, model: TextModel) -> None:
        """Inject the read-only evidence store and bounded model."""
        self._store = store
        self._model = model

    def run(self, incident_id: str) -> PatternRun:
        """Classify into an allowlisted route and execute exactly one path."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        context = _render_context(incident, evidence)
        allowed = ", ".join(category.value for category in IncidentCategory)
        classification = self._model.complete(
            system=(
                "Classify the primary investigation lens. Return exactly one lowercase label "
                f"from: {allowed}."
            ),
            prompt=context,
        )
        label = classification.text.strip().lower()
        try:
            category = IncidentCategory(label)
        except ValueError as exc:
            raise InvalidRouteError(f"classifier returned unsupported route: {label!r}") from exc

        analysis = self._model.complete(
            system=(
                f"You are on the {category.value} investigation path. "
                f"{_ROUTE_INSTRUCTIONS[category]} Use only supplied evidence."
            ),
            prompt=context,
        )
        return PatternRun(
            pattern=AutonomyPattern.ROUTING,
            incident_id=incident.incident_id,
            answer=analysis.text,
            model_calls=2,
            tool_calls=0,
            steps=("classify", f"route:{category.value}", "model-analysis"),
            usage=classification.usage + analysis.usage,
            latency_ms=(perf_counter() - started) * 1000,
        )
