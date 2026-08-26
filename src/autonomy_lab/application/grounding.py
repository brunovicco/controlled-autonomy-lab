"""Deterministic grounding checks against the bounded incident fixture."""

import re
from collections.abc import Iterable

from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.grounding import (
    GroundingFinding,
    GroundingFindingKind,
    GroundingReport,
)

_VERSION_RE = re.compile(r"(?<![\w.])v\d+\.\d+\.\d+(?![\w.])", re.IGNORECASE)
_TIME_RE = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)")
_NUMBER_PATTERN = r"(?:\d{1,3}(?:[,\u202f\xa0 ]\d{3})+|\d+)(?:\.\d+)?"
_MEASUREMENT_RE = re.compile(
    rf"(?<![\w.]){_NUMBER_PATTERN}"
    rf"(?:\s*[–—-]\s*{_NUMBER_PATTERN})?"
    r"\s*(?:%|pp|ms|milliseconds?|secs?|seconds?|s|mins?|minutes?|hours?|hrs?)"
    r"(?!\w)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_CAUSALITY_RE = re.compile(
    r"\b(?:caused|causes|causing|root cause|resulted in|results in|led to|leads to|due to)\b",
    re.IGNORECASE,
)
_UNCERTAINTY_RE = re.compile(
    r"\b(?:hypothes\w*|plausib\w*|possib\w*|may|might|could|likely|appears?\b|"
    r"suggests?\b|if\b|alternatively|correlation|not proven|cannot|can't|uncertain\w*|"
    r"unknown|assuming|would confirm|would falsify)\b",
    re.IGNORECASE,
)


def _reference_text(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    fields = [incident.incident_id, incident.service, incident.started_at, incident.symptom]
    fields.extend(item.summary for item in evidence)
    return "\n".join(fields)


def _normalize_version(value: str) -> str:
    return value.lower()


def _normalize_time(value: str) -> str:
    hour, minute = value.split(":", maxsplit=1)
    return f"{int(hour):02d}:{minute}"


def _normalize_measurement(value: str) -> str:
    normalized = value.lower().replace("\u202f", " ").replace("\xa0", " ")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(r"\s+", "", normalized).replace(",", "")
    normalized = re.sub(r"milliseconds?$", "ms", normalized)
    normalized = re.sub(r"(?:secs?|seconds?)$", "s", normalized)
    normalized = re.sub(r"(?:mins?|minutes?)$", "min", normalized)
    normalized = re.sub(r"(?:hrs?|hours?)$", "h", normalized)
    return normalized


def _context_for(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    context = " ".join(text[line_start:line_end].split())
    if len(context) <= 180:
        return context
    return f"{context[:177]}..."


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _derived_percentage_point_values(reference: str) -> set[float]:
    percentages = [float(match.group(1)) for match in _PERCENT_RE.finditer(reference)]
    return {
        round(abs(left - right), 10)
        for index, left in enumerate(percentages)
        for right in percentages[index + 1 :]
    }


def _is_supported_pp(value: str, derived_pp: set[float]) -> bool:
    if not value.endswith("pp"):
        return False
    numeric = value.removesuffix("pp")
    if "-" in numeric:
        return False
    try:
        return round(float(numeric), 10) in derived_pp
    except ValueError:
        return False


class DeterministicGroundingEvaluator:
    """Evaluate exact specifics and causal language without another model call."""

    def evaluate(
        self,
        *,
        answer: str,
        incident: Incident,
        evidence: tuple[EvidenceItem, ...],
    ) -> GroundingReport:
        """Compare answer specifics with the exact incident/evidence fixture."""
        reference = _reference_text(incident, evidence)
        supported_versions = {_normalize_version(item.group()) for item in _VERSION_RE.finditer(reference)}
        supported_times = {_normalize_time(item.group()) for item in _TIME_RE.finditer(reference)}
        supported_measurements = {
            _normalize_measurement(item.group()) for item in _MEASUREMENT_RE.finditer(reference)
        }
        derived_pp = _derived_percentage_point_values(reference)

        supported: list[str] = []
        unsupported: list[GroundingFinding] = []
        seen_unsupported: set[tuple[GroundingFindingKind, str]] = set()

        for match in _VERSION_RE.finditer(answer):
            normalized = _normalize_version(match.group())
            if normalized in supported_versions:
                supported.append(normalized)
            else:
                self._append_unsupported(
                    unsupported,
                    seen_unsupported,
                    kind=GroundingFindingKind.UNSUPPORTED_VERSION,
                    normalized=normalized,
                    value=match.group(),
                    context=_context_for(answer, match.start(), match.end()),
                )

        for match in _TIME_RE.finditer(answer):
            normalized = _normalize_time(match.group())
            if normalized in supported_times:
                supported.append(normalized)
            else:
                self._append_unsupported(
                    unsupported,
                    seen_unsupported,
                    kind=GroundingFindingKind.UNSUPPORTED_TIME,
                    normalized=normalized,
                    value=match.group(),
                    context=_context_for(answer, match.start(), match.end()),
                )

        for match in _MEASUREMENT_RE.finditer(answer):
            normalized = _normalize_measurement(match.group())
            if normalized in supported_measurements or _is_supported_pp(normalized, derived_pp):
                supported.append(normalized)
            else:
                self._append_unsupported(
                    unsupported,
                    seen_unsupported,
                    kind=GroundingFindingKind.UNSUPPORTED_MEASUREMENT,
                    normalized=normalized,
                    value=match.group(),
                    context=_context_for(answer, match.start(), match.end()),
                )

        causality = self._causality_findings(answer)
        return GroundingReport(
            supported_specifics=_unique(supported),
            unsupported_specifics=tuple(unsupported),
            causality_overclaims=causality,
            uncertainty_preserved=bool(_UNCERTAINTY_RE.search(answer)),
        )

    @staticmethod
    def _append_unsupported(
        findings: list[GroundingFinding],
        seen: set[tuple[GroundingFindingKind, str]],
        *,
        kind: GroundingFindingKind,
        normalized: str,
        value: str,
        context: str,
    ) -> None:
        key = (kind, normalized)
        if key in seen:
            return
        seen.add(key)
        findings.append(GroundingFinding(kind=kind, value=value, context=context))

    @staticmethod
    def _causality_findings(answer: str) -> tuple[GroundingFinding, ...]:
        findings: list[GroundingFinding] = []
        seen_contexts: set[str] = set()
        for raw_line in answer.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            causal = _CAUSALITY_RE.search(line)
            if causal is None or _UNCERTAINTY_RE.search(line):
                continue
            if line in seen_contexts:
                continue
            seen_contexts.add(line)
            findings.append(
                GroundingFinding(
                    kind=GroundingFindingKind.CAUSALITY_OVERCLAIM,
                    value=causal.group(),
                    context=line[:180],
                )
            )
        return tuple(findings)
