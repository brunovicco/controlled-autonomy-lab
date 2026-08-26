"""Metadata-only JSONL recorder for architecture-pattern runs."""

import json
from pathlib import Path

from autonomy_lab.domain.autonomy import PatternRun


class MetadataRunRecorder:
    """Append operational metrics without storing prompts, evidence, or model answers."""

    def __init__(self, path: Path) -> None:
        """Configure the JSONL destination."""
        self._path = path

    def append(self, run: PatternRun) -> None:
        """Write one privacy-minimized execution record."""
        payload = {
            "pattern": run.pattern.value,
            "incident_id": run.incident_id,
            "model_calls": run.model_calls,
            "tool_calls": run.tool_calls,
            "steps": list(run.steps),
            "input_tokens": run.usage.input_tokens,
            "output_tokens": run.usage.output_tokens,
            "latency_ms": round(run.latency_ms, 3),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
