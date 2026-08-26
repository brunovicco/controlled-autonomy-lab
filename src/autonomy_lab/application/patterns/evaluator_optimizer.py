"""Evaluator-optimizer workflow with deterministic retry limits."""

import json
from time import perf_counter
from typing import Any

from autonomy_lab.application.ports import IncidentStore, TextModel
from autonomy_lab.domain.autonomy import (
    AutonomyPattern,
    EvidenceItem,
    Incident,
    ModelUsage,
    PatternRun,
)
from autonomy_lab.domain.evaluation import EvaluationResult

_EVALUATION_SYSTEM = """Evaluate the draft against every criterion below.
1. Claims are grounded in supplied evidence.
2. Correlation is not presented as proven causality.
3. Next steps are concrete and reversible.
4. Missing evidence and uncertainty are explicit.
Return JSON only with this exact shape: {"passed": true|false, "feedback": ["..."]}.
"""


class InvalidEvaluationError(ValueError):
    """Raised when the evaluator violates its structured-output contract."""


class EvaluationLimitError(RuntimeError):
    """Raised when quality does not pass within the configured revision budget."""


def _context(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    evidence_text = "\n".join(f"- [{item.source}] {item.summary}" for item in evidence)
    return (
        f"Incident {incident.incident_id} / {incident.service}\n"
        f"Symptom: {incident.symptom}\n\nEvidence:\n{evidence_text}"
    )


def _parse_evaluation(text: str) -> EvaluationResult:
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidEvaluationError("evaluator did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidEvaluationError("evaluation must be a JSON object")
    passed = payload.get("passed")
    feedback = payload.get("feedback")
    if not isinstance(passed, bool):
        raise InvalidEvaluationError("evaluation.passed must be boolean")
    if not isinstance(feedback, list) or not all(isinstance(item, str) for item in feedback):
        raise InvalidEvaluationError("evaluation.feedback must be a list of strings")
    return EvaluationResult(passed=passed, feedback=tuple(feedback))


class EvaluatorOptimizerIncidentAnalysis:
    """Generate, evaluate, and revise until quality passes or the budget is exhausted."""

    def __init__(
        self,
        *,
        store: IncidentStore,
        model: TextModel,
        max_revisions: int = 2,
    ) -> None:
        """Inject dependencies and configure a finite revision budget."""
        if max_revisions < 0:
            raise ValueError("max_revisions must not be negative")
        self._store = store
        self._model = model
        self._max_revisions = max_revisions

    def run(self, incident_id: str) -> PatternRun:
        """Run a quality loop whose control flow remains owned by application code."""
        started = perf_counter()
        incident = self._store.get_incident(incident_id)
        evidence = self._store.get_evidence(incident)
        context = _context(incident, evidence)
        draft = self._model.complete(
            system=(
                "Draft a concise incident assessment using only evidence. Separate facts, "
                "hypotheses, missing evidence, and reversible next steps."
            ),
            prompt=context,
        )
        usage = ModelUsage() + draft.usage
        model_calls = 1
        revisions = 0
        steps: list[str] = ["generate"]

        while True:
            evaluation_turn = self._model.complete(
                system=_EVALUATION_SYSTEM,
                prompt=f"Evidence context:\n{context}\n\nDraft to evaluate:\n{draft.text}",
            )
            usage += evaluation_turn.usage
            model_calls += 1
            steps.append(f"evaluate:{revisions + 1}")
            evaluation = _parse_evaluation(evaluation_turn.text)
            if evaluation.passed:
                steps.append("quality-pass")
                return PatternRun(
                    pattern=AutonomyPattern.EVALUATOR_OPTIMIZER,
                    incident_id=incident.incident_id,
                    answer=draft.text,
                    model_calls=model_calls,
                    tool_calls=0,
                    steps=tuple(steps),
                    usage=usage,
                    latency_ms=(perf_counter() - started) * 1000,
                )
            if revisions >= self._max_revisions:
                raise EvaluationLimitError(
                    f"quality did not pass after {self._max_revisions} revision(s)"
                )

            feedback = "\n".join(f"- {item}" for item in evaluation.feedback)
            draft = self._model.complete(
                system=(
                    "Revise the incident assessment only to address evaluator feedback. "
                    "Keep all claims grounded in the supplied evidence."
                ),
                prompt=(
                    f"Evidence context:\n{context}\n\nCurrent draft:\n{draft.text}\n\n"
                    f"Evaluator feedback:\n{feedback}"
                ),
            )
            usage += draft.usage
            model_calls += 1
            revisions += 1
            steps.append(f"revise:{revisions}")
