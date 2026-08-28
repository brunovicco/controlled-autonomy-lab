"""Deterministic hard guards for claim-level authority decisions."""

import re

from autonomy_lab.application.grounding import (
    _TIME_RE,
    _measurement_matches,
    _normalize_measurement,
    _normalize_time,
    _reference_time_measurement_associations,
)
from autonomy_lab.domain.autonomy import EvidenceItem, Incident

_INCIDENT_ID_RE = re.compile(r"\bINC-\d+\b", re.IGNORECASE)
_CURRENT_CONTEXT_RE = re.compile(r"\b(?:current|this)\s+(?:incident|outage|event)\b", re.IGNORECASE)
_CAUSALITY_RE = re.compile(
    r"\b(?:caused|causes|causing|root cause|resulted in|results in|led to|leads to|due to)\b",
    re.IGNORECASE,
)
_HISTORICAL_CAUSAL_REJECTION_RE = re.compile(
    r"\b(?:(?:does|do|did)\s+not|cannot|can't|never)\s+"
    r"(?:prove|confirm|establish|show|demonstrate)\b|"
    r"\b(?:not proven|no evidence|historical context only|context only)\b",
    re.IGNORECASE,
)
_AT_TIME_RE = re.compile(r"\bat\s*$", re.IGNORECASE)
_TIME_SUFFIX_RELATION_RE = re.compile(r"^\s*(?:[:,=]|[-=]?>|→)")


def _reference_text(evidence: tuple[EvidenceItem, ...]) -> str:
    return "\n".join(item.summary for item in evidence)


def _has_explicit_time_relation(
    claim: str,
    *,
    time_start: int,
    time_end: int,
    measurement_start: int,
) -> bool:
    before_time = claim[max(0, time_start - 12) : time_start]
    if _AT_TIME_RE.search(before_time):
        return True
    if time_end <= measurement_start:
        between = claim[time_end:measurement_start]
        return bool(_TIME_SUFFIX_RELATION_RE.match(between))
    before_time_from_measurement = claim[measurement_start:time_start]
    return bool(re.search(r"\bat\s*$", before_time_from_measurement, re.IGNORECASE))


def has_unsupported_explicit_time_measurement_association(
    claim: str,
    *,
    evidence: tuple[EvidenceItem, ...],
) -> bool:
    """Detect one explicitly stated time-to-measurement relation contradicted by the fixture."""
    times = list(_TIME_RE.finditer(claim))
    measurements = list(_measurement_matches(claim))
    if len(times) != 1 or len(measurements) != 1:
        return False

    time_match = times[0]
    measurement_match = measurements[0]
    normalized_time = _normalize_time(time_match.group())
    normalized_measurement = _normalize_measurement(measurement_match.group())

    reference = _reference_text(evidence)
    supported_measurements = {
        _normalize_measurement(item.group()) for item in _measurement_matches(reference)
    }
    if normalized_measurement not in supported_measurements:
        return False

    supported_associations = _reference_time_measurement_associations(reference)
    if (normalized_time, normalized_measurement) in supported_associations:
        return False

    return _has_explicit_time_relation(
        claim,
        time_start=time_match.start(),
        time_end=time_match.end(),
        measurement_start=measurement_match.start(),
    )


def promotes_historical_context_to_current_causality(
    claim: str,
    *,
    incident: Incident,
    evidence: tuple[EvidenceItem, ...],
) -> bool:
    """Reject historical evidence promoted into an unqualified cause for the current incident."""
    if _HISTORICAL_CAUSAL_REJECTION_RE.search(claim):
        return False

    claim_ids = {item.upper() for item in _INCIDENT_ID_RE.findall(claim)}
    reference_ids = {
        item.upper()
        for evidence_item in evidence
        for item in _INCIDENT_ID_RE.findall(evidence_item.summary)
    }
    historical_ids = (claim_ids & reference_ids) - {incident.incident_id.upper()}
    if not historical_ids:
        return False

    current = _CURRENT_CONTEXT_RE.search(claim)
    causal = _CAUSALITY_RE.search(claim)
    if current is None or causal is None or causal.start() < current.start():
        return False

    return causal.start() - current.end() <= 80
