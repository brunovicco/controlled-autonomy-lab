"""Deterministic grounding checks against the bounded incident fixture."""

import re
from collections.abc import Iterable, Iterator
from decimal import Decimal, InvalidOperation

from autonomy_lab.domain.autonomy import EvidenceItem, Incident
from autonomy_lab.domain.grounding import (
    GroundingFinding,
    GroundingFindingKind,
    GroundingReport,
)

_VERSION_RE = re.compile(r"(?<![\w.])v\d+\.\d+\.\d+(?!\w|\.\d)", re.IGNORECASE)
_TIME_RE = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)")
_INCIDENT_ID_RE = re.compile(r"\bINC-\d+\b", re.IGNORECASE)
_NUMBER_PATTERN = r"(?:\d{1,3}(?:[,\u202f\xa0 ]\d{3})+|\d+)(?:\.\d+)?"
_MEASUREMENT_RE = re.compile(
    rf"(?<![\w.]){_NUMBER_PATTERN}"
    rf"(?:\s*[\u2013\u2014-]\s*{_NUMBER_PATTERN})?"
    r"\s*(?:%|pp|ms|milliseconds?|secs?|seconds?|s|mins?|minutes?|hours?|hrs?)"
    r"(?!\w)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$", re.MULTILINE)
_BOLD_HEADING_RE = re.compile(r"^\s*\*\*(?P<title>.+?)\*\*\s*:?[ \t]*$")
_PROPOSAL_HEADING_RE = re.compile(
    r"\b(?:recommend\w*|next[- ]?steps?|actions?|plan|checks?|mitigation|remediation)\b",
    re.IGNORECASE,
)
_APPROXIMATION_PREFIX_RE = re.compile(
    r"(?:~|≈|\babout\b|\baround\b|\broughly\b|\bapprox(?:\.|imately)?\b)\s*$",
    re.IGNORECASE,
)
_SCALAR_TIME_RE = re.compile(r"(?P<number>\d+(?:\.\d+)?)(?P<unit>ms|s)$")
_CAUSALITY_RE = re.compile(
    r"\b(?:caused|causes|causing|root cause|resulted in|results in|led to|leads to|due to)\b",
    re.IGNORECASE,
)
_CAUSAL_REJECTION_RE = re.compile(
    r"\b(?:avoid\s+(?:treat(?:ing)?|assum(?:e|ing)|claim(?:ing)?|conclud(?:e|ing))|"
    r"(?:do\s+not|don't|never)\s+(?:treat|assume|claim|conclude)|"
    r"before\s+(?:declaring|claiming|concluding))\b",
    re.IGNORECASE,
)
_UNCERTAINTY_RE = re.compile(
    r"\b(?:hypothes\w*|plausib\w*|possib\w*|may|might|could|likely|appears?\b|"
    r"suggests?\b|if\b|alternatively|correlation|not proven|no confirmed|not confirmed|"
    r"unconfirmed|no evidence|cannot|can't|uncertain\w*|unknown|assuming|would confirm|"
    r"would falsify)\b",
    re.IGNORECASE,
)
_CAUSAL_TAIL_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "been",
    "by",
    "for",
    "has",
    "have",
    "is",
    "of",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
}


def _reference_text(incident: Incident, evidence: tuple[EvidenceItem, ...]) -> str:
    fields = [incident.incident_id, incident.service, incident.started_at, incident.symptom]
    fields.extend(item.summary for item in evidence)
    return "\n".join(fields)


def _normalize_version(value: str) -> str:
    return value.lower()


def _normalize_time(value: str) -> str:
    hour, minute = value.split(":", maxsplit=1)
    return f"{int(hour):02d}:{minute}"


def _decimal_text(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def _normalize_measurement(value: str) -> str:
    normalized = value.lower().replace("\u202f", " ").replace("\xa0", " ")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = re.sub(r"\s+", "", normalized).replace(",", "")
    normalized = re.sub(r"milliseconds?$", "ms", normalized)
    normalized = re.sub(r"(?:secs?|seconds?)$", "s", normalized)
    normalized = re.sub(r"(?:mins?|minutes?)$", "min", normalized)
    normalized = re.sub(r"(?:hrs?|hours?)$", "h", normalized)

    scalar_time = _SCALAR_TIME_RE.fullmatch(normalized)
    if scalar_time is None:
        return normalized
    try:
        numeric = Decimal(scalar_time.group("number"))
    except InvalidOperation:
        return normalized
    if scalar_time.group("unit") == "s":
        numeric *= Decimal(1000)
    return f"{_decimal_text(numeric)}ms"


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


def _measurement_matches(text: str) -> Iterator[re.Match[str]]:
    """Yield measurements while excluding spans that overlap timestamp tokens."""
    time_spans = tuple((match.start(), match.end()) for match in _TIME_RE.finditer(text))
    for match in _MEASUREMENT_RE.finditer(text):
        if any(match.start() < end and match.end() > start for start, end in time_spans):
            continue
        yield match


def _heading_title(raw_line: str) -> str | None:
    markdown = _HEADING_RE.match(raw_line)
    if markdown is not None:
        return markdown.group("title")
    bold = _BOLD_HEADING_RE.match(raw_line)
    if bold is not None:
        return bold.group("title")
    return None


def _section_heading_for(text: str, position: int) -> str:
    heading = ""
    offset = 0
    for raw_line in text[:position].splitlines(keepends=True):
        title = _heading_title(raw_line.rstrip("\r\n"))
        if title is not None:
            heading = title
        offset += len(raw_line)
        if offset >= position:
            break
    return heading


def _is_proposed_context(text: str, position: int) -> bool:
    return bool(_PROPOSAL_HEADING_RE.search(_section_heading_for(text, position)))


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


def _reference_time_measurement_associations(reference: str) -> set[tuple[str, str]]:
    """Extract exact timestamp-to-measurement pairs encoded by the fixture."""
    associations: set[tuple[str, str]] = set()
    for segment in re.split(r",\s*|\.\s+", reference):
        if "=" not in segment:
            continue
        times = list(_TIME_RE.finditer(segment))
        measurements = list(_measurement_matches(segment))
        if len(times) != 1 or len(measurements) != 1:
            continue
        associations.add(
            (
                _normalize_time(times[0].group()),
                _normalize_measurement(measurements[0].group()),
            )
        )
    return associations


def _is_explicit_approximation(text: str, position: int) -> bool:
    prefix = text[max(0, position - 24) : position]
    return bool(_APPROXIMATION_PREFIX_RE.search(prefix))


def _scalar_time_parts(value: str) -> tuple[Decimal, str, int] | None:
    compact = value.lower().replace("\u202f", " ").replace("\xa0", " ")
    compact = re.sub(r"\s+", "", compact).replace(",", "")
    compact = re.sub(r"milliseconds?$", "ms", compact)
    compact = re.sub(r"(?:secs?|seconds?)$", "s", compact)
    match = _SCALAR_TIME_RE.fullmatch(compact)
    if match is None:
        return None
    number_text = match.group("number")
    try:
        numeric = Decimal(number_text)
    except InvalidOperation:
        return None
    decimal_places = len(number_text.partition(".")[2])
    return numeric, match.group("unit"), decimal_places


def _approximate_supported_measurement(
    *,
    text: str,
    match: re.Match[str],
    supported_measurements: set[str],
) -> str | None:
    """Return the exact fixture value represented by an explicitly rounded time measurement."""
    if not _is_explicit_approximation(text, match.start()):
        return None
    candidate = _scalar_time_parts(match.group())
    if candidate is None:
        return None
    candidate_value, candidate_unit, decimal_places = candidate
    quantum = Decimal(1).scaleb(-decimal_places)

    for supported in supported_measurements:
        reference = _scalar_time_parts(supported)
        if reference is None:
            continue
        reference_value, reference_unit, _ = reference
        if reference_unit == "ms" and candidate_unit == "s":
            reference_value /= Decimal(1000)
        elif reference_unit == "s" and candidate_unit == "ms":
            reference_value *= Decimal(1000)
        if reference_value.quantize(quantum) == candidate_value:
            return supported
    return None


def _markdown_table_association_findings(
    *,
    answer: str,
    supported_measurements: set[str],
    supported_associations: set[tuple[str, str]],
) -> tuple[GroundingFinding, ...]:
    """Flag supported values attached to an unsupported timestamp in Markdown table rows."""
    findings: list[GroundingFinding] = []
    seen: set[tuple[str, str]] = set()
    offset = 0
    for raw_line in answer.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            offset += len(raw_line)
            continue
        if _is_proposed_context(answer, offset):
            offset += len(raw_line)
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            offset += len(raw_line)
            continue
        row_times = list(_TIME_RE.finditer(cells[0]))
        if len(row_times) != 1:
            offset += len(raw_line)
            continue
        row_time = _normalize_time(row_times[0].group())
        for cell in cells[1:]:
            if _TIME_RE.search(cell):
                continue
            for match in _measurement_matches(cell):
                normalized = _normalize_measurement(match.group())
                canonical = normalized if normalized in supported_measurements else None
                if canonical is None:
                    canonical = _approximate_supported_measurement(
                        text=cell,
                        match=match,
                        supported_measurements=supported_measurements,
                    )
                if canonical is None:
                    continue
                pair = (row_time, canonical)
                if pair in supported_associations or pair in seen:
                    continue
                seen.add(pair)
                context = " ".join(line.split())
                if len(context) > 180:
                    context = f"{context[:177]}..."
                findings.append(
                    GroundingFinding(
                        kind=GroundingFindingKind.UNSUPPORTED_ASSOCIATION,
                        value=f"{row_time} -> {canonical}",
                        context=context,
                    )
                )
        offset += len(raw_line)
    return tuple(findings)


def _word_tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", text)}


def _supported_historical_causality(
    *,
    line: str,
    causal: re.Match[str],
    reference: str,
    current_incident_id: str,
) -> bool:
    """Accept a causal statement about a prior incident only when its causal detail is evidenced."""
    line_ids = {item.upper() for item in _INCIDENT_ID_RE.findall(line)}
    reference_ids = {item.upper() for item in _INCIDENT_ID_RE.findall(reference)}
    historical_ids = (line_ids & reference_ids) - {current_incident_id.upper()}
    if not historical_ids:
        return False

    tail_tokens = _word_tokens(line[causal.end() :]) - _CAUSAL_TAIL_STOPWORDS
    if not tail_tokens:
        return False

    for incident_id in historical_ids:
        evidence_lines = [
            reference_line
            for reference_line in reference.splitlines()
            if incident_id.lower() in reference_line.lower()
        ]
        evidence_tokens = _word_tokens(" ".join(evidence_lines))
        if tail_tokens.issubset(evidence_tokens):
            return True
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
        supported_versions = {
            _normalize_version(item.group()) for item in _VERSION_RE.finditer(reference)
        }
        supported_times = {_normalize_time(item.group()) for item in _TIME_RE.finditer(reference)}
        supported_measurements = {
            _normalize_measurement(item.group()) for item in _measurement_matches(reference)
        }
        derived_pp = _derived_percentage_point_values(reference)
        supported_associations = _reference_time_measurement_associations(reference)

        supported: list[str] = []
        unsupported: list[GroundingFinding] = []
        proposed: list[GroundingFinding] = []
        seen_unsupported: set[tuple[GroundingFindingKind, str]] = set()
        seen_proposed: set[tuple[GroundingFindingKind, str]] = set()

        for match in _VERSION_RE.finditer(answer):
            normalized = _normalize_version(match.group())
            if normalized in supported_versions:
                supported.append(normalized)
            else:
                self._append_finding(
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
                continue
            if _is_proposed_context(answer, match.start()):
                self._append_finding(
                    proposed,
                    seen_proposed,
                    kind=GroundingFindingKind.PROPOSED_PARAMETER,
                    normalized=normalized,
                    value=match.group(),
                    context=_context_for(answer, match.start(), match.end()),
                )
                continue
            self._append_finding(
                unsupported,
                seen_unsupported,
                kind=GroundingFindingKind.UNSUPPORTED_TIME,
                normalized=normalized,
                value=match.group(),
                context=_context_for(answer, match.start(), match.end()),
            )

        for match in _measurement_matches(answer):
            normalized = _normalize_measurement(match.group())
            approximate_reference = _approximate_supported_measurement(
                text=answer,
                match=match,
                supported_measurements=supported_measurements,
            )
            if normalized in supported_measurements or _is_supported_pp(normalized, derived_pp):
                supported.append(normalized)
                continue
            if approximate_reference is not None:
                supported.append(approximate_reference)
                continue
            if _is_proposed_context(answer, match.start()):
                self._append_finding(
                    proposed,
                    seen_proposed,
                    kind=GroundingFindingKind.PROPOSED_PARAMETER,
                    normalized=normalized,
                    value=match.group(),
                    context=_context_for(answer, match.start(), match.end()),
                )
                continue
            self._append_finding(
                unsupported,
                seen_unsupported,
                kind=GroundingFindingKind.UNSUPPORTED_MEASUREMENT,
                normalized=normalized,
                value=match.group(),
                context=_context_for(answer, match.start(), match.end()),
            )

        unsupported.extend(
            _markdown_table_association_findings(
                answer=answer,
                supported_measurements=supported_measurements,
                supported_associations=supported_associations,
            )
        )

        causality = self._causality_findings(
            answer,
            reference=reference,
            current_incident_id=incident.incident_id,
        )
        return GroundingReport(
            supported_specifics=_unique(supported),
            unsupported_specifics=tuple(unsupported),
            causality_overclaims=causality,
            uncertainty_preserved=bool(_UNCERTAINTY_RE.search(answer)),
            proposed_specifics=tuple(proposed),
        )

    @staticmethod
    def _append_finding(
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
    def _causality_findings(
        answer: str,
        *,
        reference: str,
        current_incident_id: str,
    ) -> tuple[GroundingFinding, ...]:
        findings: list[GroundingFinding] = []
        seen_contexts: set[str] = set()
        active_heading = ""
        for raw_line in answer.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            heading = _heading_title(raw_line)
            if heading is not None:
                active_heading = heading
                continue
            causal = _CAUSALITY_RE.search(line)
            section_is_qualified = bool(_UNCERTAINTY_RE.search(active_heading))
            if (
                causal is None
                or _UNCERTAINTY_RE.search(line)
                or _CAUSAL_REJECTION_RE.search(line)
                or section_is_qualified
            ):
                continue
            if _supported_historical_causality(
                line=line,
                causal=causal,
                reference=reference,
                current_incident_id=current_incident_id,
            ):
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
