"""Loader for packaged human-labelled claim evaluation fixtures."""

import json
from collections.abc import Mapping
from importlib.resources import files
from typing import Any

from autonomy_lab.domain.claim_evaluation import ClaimKind
from autonomy_lab.domain.claim_matrix import LabelledClaimCase, LabelledClaimSet


class LabelledClaimSetError(ValueError):
    """Raised when a packaged labelled claim set violates its static contract."""


def load_labelled_claims_v1() -> LabelledClaimSet:
    """Load and validate the packaged v1 claim set."""
    raw = (
        files("autonomy_lab.evals").joinpath("labelled_claims_v1.json").read_text(encoding="utf-8")
    )
    try:
        decoded: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LabelledClaimSetError("labelled claim set is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise LabelledClaimSetError("labelled claim set root must be an object")

    name = _required_string(decoded, "name")
    version = _required_string(decoded, "version")
    incident_id = _required_string(decoded, "incident_id")
    cases_raw = decoded.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise LabelledClaimSetError("labelled claim set cases must be a non-empty list")

    cases: list[LabelledClaimCase] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(cases_raw):
        if not isinstance(item, Mapping):
            raise LabelledClaimSetError(f"claim case {index} must be an object")
        case_id = _required_string(item, "id")
        if case_id in seen_ids:
            raise LabelledClaimSetError(f"duplicate claim case id: {case_id}")
        seen_ids.add(case_id)

        expected_raw = _required_string(item, "expected_kind")
        try:
            expected_kind = ClaimKind(expected_raw)
        except ValueError as exc:
            raise LabelledClaimSetError(
                f"claim case {case_id} has unsupported expected_kind: {expected_raw}"
            ) from exc

        notes_raw = item.get("notes", "")
        if not isinstance(notes_raw, str):
            raise LabelledClaimSetError(f"claim case {case_id} notes must be a string")

        cases.append(
            LabelledClaimCase(
                case_id=case_id,
                category=_required_string(item, "category"),
                answer=_required_string(item, "answer"),
                expected_kind=expected_kind,
                notes=notes_raw.strip(),
            )
        )

    return LabelledClaimSet(
        name=name,
        version=version,
        incident_id=incident_id,
        cases=tuple(cases),
    )


def _required_string(item: Mapping[str, object], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LabelledClaimSetError(f"labelled claim field {field!r} must be a non-empty string")
    return value.strip()
