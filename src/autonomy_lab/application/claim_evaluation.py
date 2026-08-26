"""Conservative deterministic baseline for claim-level evaluation v2."""

import re
from dataclasses import dataclass

from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.claim_evaluation import ClaimEvaluation, ClaimEvaluationReport, ClaimKind

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$")
_BOLD_HEADING_RE = re.compile(r"^\s*\*\*(?P<title>.+?)\*\*\s*:?[ \t]*$")
_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`*])")
_PROPOSAL_HEADING_RE = re.compile(
    r"\b(?:recommend\w*|next[- ]?steps?|actions?|plan|checks?|mitigation|remediation)\b",
    re.IGNORECASE,
)
_HYPOTHESIS_HEADING_RE = re.compile(
    r"\b(?:hypothes\w*|assessment|interpretation|analysis)\b",
    re.IGNORECASE,
)
_INFERENCE_RE = re.compile(
    r"\b(?:hypothes\w*|plausib\w*|possib\w*|may|might|could|likely|appears?\b|"
    r"suggests?\b|consistent with|supports?\b|correlat\w*|interaction)\b",
    re.IGNORECASE,
)
_EPISTEMIC_INFERENCE_RE = re.compile(
    r"^(?:no confirmed|not confirmed|unconfirmed|no evidence)\b",
    re.IGNORECASE,
)
_IMPERATIVE_RE = re.compile(
    r"^(?:compare|check|monitor|collect|inspect|validate|confirm|consider|prefer|"
    r"route|restore|revert|roll back|rollback|temporarily|escalate|review|measure|continue)\b",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NEGATION_RE = re.compile(r"\b(?:no|not|without|never)\b", re.IGNORECASE)
_HIGH_CONFIDENCE_PARAPHRASE_SOURCES = frozenset({"deployments", "dependencies"})
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "there",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass(frozen=True, slots=True)
class _ClaimCandidate:
    text: str
    heading: str
    list_item: bool


def _heading_title(line: str) -> str | None:
    markdown = _HEADING_RE.match(line)
    if markdown is not None:
        return markdown.group("title")
    bold = _BOLD_HEADING_RE.match(line)
    if bold is not None:
        return bold.group("title")
    return None


def _extract_claims(answer: str) -> tuple[_ClaimCandidate, ...]:
    """Extract non-heading, non-empty sentence-like claims while retaining section context."""
    heading = ""
    claims: list[_ClaimCandidate] = []
    for raw_line in answer.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        title = _heading_title(stripped)
        if title is not None:
            heading = title
            continue
        list_item = _LIST_PREFIX_RE.match(stripped) is not None
        content = _LIST_PREFIX_RE.sub("", stripped).strip()
        if not content:
            continue
        for sentence in _SENTENCE_BOUNDARY_RE.split(content):
            claim = sentence.strip()
            if claim:
                claims.append(
                    _ClaimCandidate(
                        text=claim,
                        heading=heading,
                        list_item=list_item,
                    )
                )
    return tuple(claims)


def _normalized_text(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.lower().replace("-", " ")))


def _content_tokens(value: str) -> set[str]:
    return set(_normalized_text(value).split()) - _STOPWORDS


def _reference_text(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    fields = [incident.incident_id, incident.service, incident.started_at, incident.symptom]
    fields.extend(item.summary for item in evidence)
    return "\n".join(fields)


def _evidence_sources_for(claim: str, evidence: tuple[EvidenceItem, ...]) -> tuple[str, ...]:
    claim_tokens = _content_tokens(claim)
    if not claim_tokens:
        return ()
    sources: list[str] = []
    for item in evidence:
        overlap = claim_tokens & _content_tokens(item.summary)
        if len(overlap) >= 2:
            sources.append(item.source)
    return tuple(dict.fromkeys(sources))


def _is_direct_textual_support(
    claim: str,
    *,
    incident: Incident,
    evidence: tuple[EvidenceItem, ...],
) -> bool:
    normalized_claim = _normalized_text(claim)
    if len(normalized_claim.split()) < 3:
        return False
    return normalized_claim in _normalized_text(_reference_text(incident, evidence))


def _shared_content_ngram(left: str, right: str, *, size: int) -> bool:
    left_tokens = [token for token in _normalized_text(left).split() if token not in _STOPWORDS]
    right_tokens = [token for token in _normalized_text(right).split() if token not in _STOPWORDS]
    if len(left_tokens) < size or len(right_tokens) < size:
        return False
    left_ngrams = {
        tuple(left_tokens[index : index + size]) for index in range(len(left_tokens) - size + 1)
    }
    return any(
        tuple(right_tokens[index : index + size]) in left_ngrams
        for index in range(len(right_tokens) - size + 1)
    )


def _has_high_confidence_fixture_support(
    claim: str,
    *,
    evidence: tuple[EvidenceItem, ...],
) -> bool:
    """Recognize bounded near-verbatim paraphrases without attempting general entailment."""
    claim_tokens = _content_tokens(claim)
    if len(claim_tokens) < 4:
        return False
    claim_negated = _NEGATION_RE.search(claim) is not None
    for item in evidence:
        if item.source not in _HIGH_CONFIDENCE_PARAPHRASE_SOURCES:
            continue
        if claim_negated != (_NEGATION_RE.search(item.summary) is not None):
            continue
        evidence_tokens = _content_tokens(item.summary)
        coverage = len(claim_tokens & evidence_tokens) / len(claim_tokens)
        if coverage >= 0.8:
            return True
        if coverage >= 0.7 and _shared_content_ngram(claim, item.summary, size=3):
            return True
    return False


def _is_proposed(candidate: _ClaimCandidate) -> bool:
    section_action = bool(_PROPOSAL_HEADING_RE.search(candidate.heading)) and candidate.list_item
    return bool(section_action or _IMPERATIVE_RE.match(candidate.text))


def _is_inference(candidate: _ClaimCandidate) -> bool:
    return bool(
        _INFERENCE_RE.search(candidate.text)
        or _EPISTEMIC_INFERENCE_RE.search(candidate.text)
        or _HYPOTHESIS_HEADING_RE.search(candidate.heading)
    )


class DeterministicClaimEvaluatorV2:
    """Classify claims conservatively using fixture evidence plus Grounding v1 hard signals.

    This baseline intentionally does not pretend to perform semantic entailment. A semantic
    evaluator may upgrade paraphrases or nuanced inferences, but it must not erase deterministic
    unsupported-specific or causality findings. A small bounded near-verbatim matcher handles
    high-confidence deployment/dependency paraphrases before semantic escalation.
    """

    def __init__(
        self,
        *,
        grounding_evaluator: DeterministicGroundingEvaluator | None = None,
    ) -> None:
        """Configure the deterministic hard-signal evaluator dependency."""
        self._grounding = grounding_evaluator or DeterministicGroundingEvaluator()

    def evaluate(
        self,
        *,
        answer: str,
        incident: Incident,
        evidence: tuple[EvidenceItem, ...],
    ) -> ClaimEvaluationReport:
        """Extract and classify claims from one model answer."""
        evaluations = tuple(
            self._classify(candidate, incident=incident, evidence=evidence)
            for candidate in _extract_claims(answer)
        )
        return ClaimEvaluationReport(claims=evaluations)

    def _classify(
        self,
        candidate: _ClaimCandidate,
        *,
        incident: Incident,
        evidence: tuple[EvidenceItem, ...],
    ) -> ClaimEvaluation:
        sources = _evidence_sources_for(candidate.text, evidence)

        if _is_proposed(candidate):
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.PROPOSED_ACTION,
                rationale="proposal-context",
                evidence_sources=sources,
            )

        grounding = self._grounding.evaluate(
            answer=candidate.text,
            incident=incident,
            evidence=evidence,
        )
        if grounding.unsupported_count:
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.UNSUPPORTED_CLAIM,
                rationale=f"grounding-v1-unsupported-specifics:{grounding.unsupported_count}",
                evidence_sources=sources,
            )
        if grounding.causality_overclaim_count:
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.UNSUPPORTED_CLAIM,
                rationale=f"grounding-v1-causality-overclaim:{grounding.causality_overclaim_count}",
                evidence_sources=sources,
            )

        if _is_direct_textual_support(
            candidate.text,
            incident=incident,
            evidence=evidence,
        ) or _has_high_confidence_fixture_support(candidate.text, evidence=evidence):
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.SUPPORTED_FACT,
                rationale="deterministic-fixture-support",
                evidence_sources=sources,
            )

        if _is_inference(candidate):
            if sources:
                return ClaimEvaluation(
                    claim=candidate.text,
                    kind=ClaimKind.SUPPORTED_INFERENCE,
                    rationale="qualified-inference-with-evidence-anchor",
                    evidence_sources=sources,
                )
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.UNSUPPORTED_CLAIM,
                rationale="inference-without-evidence-anchor",
            )

        if grounding.supported_specifics:
            return ClaimEvaluation(
                claim=candidate.text,
                kind=ClaimKind.SUPPORTED_FACT,
                rationale="deterministic-fixture-support",
                evidence_sources=sources,
            )

        return ClaimEvaluation(
            claim=candidate.text,
            kind=ClaimKind.UNSUPPORTED_CLAIM,
            rationale="deterministic-v2-no-direct-support",
            evidence_sources=sources,
        )
