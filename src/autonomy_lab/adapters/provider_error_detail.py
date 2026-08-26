"""Safe extraction of bounded provider error metadata."""

import json
import re
from collections.abc import Mapping
from typing import Any

_SECRET_TOKEN_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_MAX_DETAIL_CHARS = 280


def safe_provider_error_detail(raw: bytes, *, secret: str = "") -> str | None:
    """Extract only bounded, sanitized fields from a provider JSON error response."""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return None

    parts: list[str] = []
    error_type = _safe_scalar(error.get("type"))
    error_code = _safe_scalar(error.get("code"))
    message = error.get("message")

    if error_type:
        parts.append(f"type={error_type}")
    if error_code:
        parts.append(f"code={error_code}")
    if isinstance(message, str) and message.strip():
        parts.append(f"message={_sanitize_message(message, secret=secret)}")
    if not parts:
        return None
    return "; ".join(parts)[:_MAX_DETAIL_CHARS]


def _safe_scalar(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return _sanitize_message(value, secret="")[:80]
    if isinstance(value, int):
        return str(value)
    return None


def _sanitize_message(message: str, *, secret: str) -> str:
    compact = " ".join(message.split())
    if secret:
        compact = compact.replace(secret, "[REDACTED]")
    compact = _SECRET_TOKEN_RE.sub("[REDACTED]", compact)
    return _BEARER_RE.sub("Bearer [REDACTED]", compact)
