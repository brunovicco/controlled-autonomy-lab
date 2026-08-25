"""Single-call augmented LLM baseline for incident analysis."""

from time import perf_counter

from harness_example.application.ports import IncidentStore, TextModel
from harness_example.domain.autonomy import AutonomyPattern, EvidenceItem, Incident, PatternRun

_SYSTEM = """You are a production incident analyst.
Use only the supplied evidence. Separate observed facts from hypotheses. Never turn timing
correlation into a confirmed causal claim. Recommend reversible next steps and explicitly name
missing evidence when the root cause is not proven.
"""


def _format_prompt(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    evidence_text = "\n".join(f"- [{item.source}] {item.summary}" for item in evidence)
    return (
        f"Incident: {incident.incident_id}\n"
        f"Service: {incident.service}\n"
        f"Started: {incident.started_at}\n"
        f"Symptom: {incident.symptom}\n\n"
        f"Evidence:\n{evidence_text}\n\n"
        "Return a concise incident assessment with: observed facts, ranked hypotheses, "
        "recommended next checks, and confidence."
    )


class AugmentedIncidentAnalysis:
    """Analyze an incident with retrieval plus exactly one model call."""

    def __init__(self, *, store: IncidentStore, model: TextModel) -> None:
        """Inject the read-only evidence store and bounded text model."""
        self._store = store
        self._model = model

    def run(self, incident_id: str) -> PatternRun:
        """Run the high-predictability, low-autonomy baseline."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        turn = self._model.complete(system=_SYSTEM, prompt=_format_prompt(incident, evidence))
        latency_ms = (perf_counter() - started) * 1000
        return PatternRun(
            pattern=AutonomyPattern.AUGMENTED,
            incident_id=incident.incident_id,
            answer=turn.text,
            model_calls=1,
            tool_calls=0,
            steps=("load-evidence", "model-analysis"),
            usage=turn.usage,
            latency_ms=latency_ms,
        )
