"""Parallel fan-out/fan-in workflow for incident analysis."""

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from harness_example.application.ports import IncidentStore, TextModel
from harness_example.domain.autonomy import (
    AutonomyPattern,
    EvidenceItem,
    Incident,
    ModelUsage,
    PatternRun,
)

_FOCUS_AREAS = (
    (
        "metrics",
        "Analyze error-rate and latency evidence. Do not infer causes from timing alone.",
    ),
    (
        "changes",
        "Analyze recent deployment/configuration evidence and rollback relevance.",
    ),
    (
        "dependencies",
        "Analyze dependency evidence and what would confirm or falsify that hypothesis.",
    ),
)


def _context(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    items = "\n".join(f"- [{item.source}] {item.summary}" for item in evidence)
    return f"{incident.incident_id} / {incident.service} / {incident.symptom}\n\n{items}"


class ParallelIncidentAnalysis:
    """Run independent specialist calls concurrently, then aggregate them."""

    def __init__(self, *, store: IncidentStore, model: TextModel) -> None:
        """Inject the read-only evidence store and bounded model."""
        self._store = store
        self._model = model

    def run(self, incident_id: str) -> PatternRun:
        """Execute three independent calls concurrently and one deterministic fan-in."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        context = _context(incident, evidence)

        with ThreadPoolExecutor(max_workers=len(_FOCUS_AREAS)) as executor:
            futures = {
                name: executor.submit(
                    self._model.complete,
                    system=instruction,
                    prompt=f"Focus: {name}\n\n{context}",
                )
                for name, instruction in _FOCUS_AREAS
            }
            specialist_turns = {name: futures[name].result() for name, _ in _FOCUS_AREAS}

        specialist_text = "\n\n".join(
            f"[{name}]\n{specialist_turns[name].text}" for name, _ in _FOCUS_AREAS
        )
        aggregate = self._model.complete(
            system=(
                "Aggregate independent specialist findings. Preserve disagreements and "
                "uncertainty; return ranked hypotheses and reversible next checks."
            ),
            prompt=expert_prompt(incident, specialist_text),
        )
        usage = ModelUsage()
        for name, _ in _FOCUS_AREAS:
            usage += specialist_turns[name].usage
        usage += aggregate.usage
        return PatternRun(
            pattern=AutonomyPattern.PARALLEL,
            incident_id=incident.incident_id,
            answer=aggregate.text,
            model_calls=4,
            tool_calls=0,
            steps=("fan-out:3", "fan-in", "aggregate"),
            usage=usage,
            latency_ms=(perf_counter() - started) * 1000,
        )


def expert_prompt(incident: Incident, specialist_text: str) -> str:
    """Build the deterministic aggregation handoff."""
    return (
        f"Incident {incident.incident_id} on {incident.service}.\n\n"
        f"Specialist findings:\n{specialist_text}"
    )
