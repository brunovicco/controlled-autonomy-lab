"""Sequential prompt-chaining workflow for incident analysis."""

from time import perf_counter

from harness_example.application.ports import IncidentStore, TextModel
from harness_example.domain.autonomy import AutonomyPattern, EvidenceItem, Incident, ModelUsage, PatternRun


def _evidence_text(evidence: tuple[EvidenceItem, ...]) -> str:
    return "\n".join(f"- [{item.source}] {item.summary}" for item in evidence)


def _incident_text(incident: Incident) -> str:
    return (
        f"Incident={incident.incident_id}; service={incident.service}; "
        f"started={incident.started_at}; symptom={incident.symptom}"
    )


class ChainedIncidentAnalysis:
    """Execute a fixed extract -> assess -> recommend model workflow."""

    def __init__(self, *, store: IncidentStore, model: TextModel) -> None:
        """Inject the read-only evidence store and bounded model."""
        self._store = store
        self._model = model

    def run(self, incident_id: str) -> PatternRun:
        """Run three sequential model calls with deterministic handoffs."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        evidence_text = _evidence_text(evidence)

        facts = self._model.complete(
            system="Extract only facts explicitly supported by the supplied evidence.",
            prompt=f"{_incident_text(incident)}\n\nEvidence:\n{evidence_text}",
        )
        assessment = self._model.complete(
            system=(
                "Assess severity and rank hypotheses. Treat the extracted facts as evidence, "
                "not proof of causality."
            ),
            prompt=f"Incident: {_incident_text(incident)}\n\nExtracted facts:\n{facts.text}",
        )
        recommendation = self._model.complete(
            system=(
                "Draft reversible next steps from the supplied assessment. Name missing evidence "
                "and avoid unsupported causal claims."
            ),
            prompt=(
                f"Incident: {_incident_text(incident)}\n\nFacts:\n{facts.text}\n\n"
                f"Assessment:\n{assessment.text}"
            ),
        )
        usage = ModelUsage() + facts.usage + assessment.usage + recommendation.usage
        return PatternRun(
            pattern=AutonomyPattern.CHAINING,
            incident_id=incident.incident_id,
            answer=recommendation.text,
            model_calls=3,
            tool_calls=0,
            steps=("extract-facts", "assess", "recommend"),
            usage=usage,
            latency_ms=(perf_counter() - started) * 1000,
        )
