"""Deterministic posture-aware epistemic evaluation."""

import re

from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.epistemic import EpistemicReport, EpistemicVerdict, EvidencePosture

_CONFIRMED_CAUSE_RE = re.compile(
    r"\broot cause confirmed for\s+(?P<incident>INC-\d+)\b",
    re.IGNORECASE,
)
_INCONCLUSIVE_RE = re.compile(
    r"\broot cause remains unconfirmed for\s+(?P<incident>INC-\d+)\b",
    re.IGNORECASE,
)
_CAUSALITY_RE = re.compile(
    r"\b(?:caused|causes|causing|contribute|contributed|contributes|contributing|root cause|"
    r"resulted in|results in|led to|leads to|due to)\b",
    re.IGNORECASE,
)
_HEDGE_RE = re.compile(
    r"\b(?:hypothes\w*|plausib\w*|possib\w*|may|might|could|likely|appears?|suggests?)\b",
    re.IGNORECASE,
)
_ABSTENTION_RE = re.compile(
    r"\b(?:root cause (?:remains |is )?unconfirmed|cause (?:remains |is )?unknown|"
    r"cannot determine|can't determine|cannot attribute|can't attribute|"
    r"insufficient evidence|not enough evidence|no causal conclusion|"
    r"causality is not proven|causality is unproven|not proven to have caused|"
    r"before attributing (?:a )?cause|before claiming causality)\b",
    re.IGNORECASE,
)
_CAUSAL_REJECTION_RE = re.compile(
    r"\b(?:does not prove|doesn't prove|do not claim|don't claim|"
    r"do not conclude|don't conclude|does not establish|doesn't establish|"
    r"not evidence of (?:the )?(?:current )?(?:root )?cause)\b",
    re.IGNORECASE,
)
_UNCERTAINTY_LANGUAGE_RE = re.compile(
    r"\b(?:hypothes\w*|plausib\w*|possib\w*|may|might|could|likely|appears?|"
    r"suggests?|correlation|not proven|unconfirmed|unknown|cannot|can't|"
    r"insufficient evidence|not enough evidence)\b",
    re.IGNORECASE,
)
_INCIDENT_ID_RE = re.compile(r"\bINC-\d+\b", re.IGNORECASE)
_HISTORICAL_RE = re.compile(
    r"\b(?:historical|previous incident|prior incident|past incident)\b",
    re.IGNORECASE,
)


def _reference_text(evidence: tuple[EvidenceItem, ...]) -> str:
    return "\n".join(item.summary for item in evidence)


def infer_evidence_posture(
    *,
    incident: Incident,
    evidence: tuple[EvidenceItem, ...],
) -> EvidencePosture:
    """Infer the causal authority explicitly encoded by the bounded fixture."""
    reference = _reference_text(evidence)

    for match in _CONFIRMED_CAUSE_RE.finditer(reference):
        if match.group("incident").upper() == incident.incident_id.upper():
            return EvidencePosture.CONFIRMED_CAUSE

    for match in _INCONCLUSIVE_RE.finditer(reference):
        if match.group("incident").upper() == incident.incident_id.upper():
            return EvidencePosture.INCONCLUSIVE

    return EvidencePosture.CORRELATIONAL


def _sentences(answer: str) -> tuple[str, ...]:
    return tuple(
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+|\n+", answer)
        if segment.strip()
    )


def _is_historical_sentence(sentence: str, incident: Incident) -> bool:
    if _HISTORICAL_RE.search(sentence):
        return True
    incident_ids = {value.upper() for value in _INCIDENT_ID_RE.findall(sentence)}
    return bool(incident_ids and incident.incident_id.upper() not in incident_ids)


def _causal_signals(answer: str, incident: Incident) -> tuple[bool, bool, bool]:
    causal_assertion = False
    hedged_causal = False
    abstention = bool(_ABSTENTION_RE.search(answer))

    for sentence in _sentences(answer):
        if _is_historical_sentence(sentence, incident):
            continue
        if not _CAUSALITY_RE.search(sentence):
            continue
        if _ABSTENTION_RE.search(sentence) or _CAUSAL_REJECTION_RE.search(sentence):
            continue
        if _HEDGE_RE.search(sentence):
            hedged_causal = True
            continue
        causal_assertion = True

    return causal_assertion, hedged_causal, abstention


class DeterministicEpistemicEvaluator:
    """Evaluate whether an answer uses the causal authority allowed by its evidence posture."""

    def evaluate(
        self,
        *,
        answer: str,
        incident: Incident,
        evidence: tuple[EvidenceItem, ...],
    ) -> EpistemicReport:
        """Return posture alignment without changing Grounding Evaluation v1."""
        expected = infer_evidence_posture(incident=incident, evidence=evidence)
        grounding = DeterministicGroundingEvaluator().evaluate(
            answer=answer,
            incident=incident,
            evidence=evidence,
        )
        causal_assertion, hedged_causal, abstention = _causal_signals(answer, incident)

        if grounding.causality_overclaim_count > 0:
            verdict = EpistemicVerdict.OVERCLAIMED
        elif expected is EvidencePosture.CONFIRMED_CAUSE:
            if causal_assertion:
                verdict = EpistemicVerdict.ALIGNED
            elif hedged_causal or abstention:
                verdict = EpistemicVerdict.OVER_HEDGED
            else:
                verdict = EpistemicVerdict.NO_POSITION
        elif expected is EvidencePosture.INCONCLUSIVE:
            if causal_assertion:
                verdict = EpistemicVerdict.OVERCLAIMED
            elif abstention:
                verdict = EpistemicVerdict.ALIGNED
            elif hedged_causal:
                verdict = EpistemicVerdict.INSUFFICIENT_ABSTENTION
            else:
                verdict = EpistemicVerdict.NO_POSITION
        else:
            if causal_assertion:
                verdict = EpistemicVerdict.OVERCLAIMED
            elif hedged_causal or abstention:
                verdict = EpistemicVerdict.ALIGNED
            else:
                verdict = EpistemicVerdict.NO_POSITION

        return EpistemicReport(
            expected_posture=expected,
            verdict=verdict,
            causal_assertion_detected=causal_assertion,
            hedged_causal_language_detected=hedged_causal,
            abstention_detected=abstention,
            uncertainty_language_detected=bool(_UNCERTAINTY_LANGUAGE_RE.search(answer)),
            causality_overclaim_count=grounding.causality_overclaim_count,
        )
