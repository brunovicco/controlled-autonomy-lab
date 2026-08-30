import runpy
from pathlib import Path
from typing import Any


def _builder_namespace() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(root / "scripts" / "build_epistemic_v2_evidence_pack.py"))


def test_group_rows_emits_only_named_group_keys_and_metrics() -> None:
    namespace = _builder_namespace()
    group_rows = namespace["_group_rows"]

    rows = [
        {
            "provider": "openai",
            "status": "ok",
            "epistemic_verdict": "aligned",
            "grounding_ratio": 1.0,
            "causality_overclaims": 0,
            "model_calls": 1,
            "tool_calls": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "latency_ms": 100.0,
        }
    ]

    summaries = group_rows(rows, ("provider",))

    assert len(summaries) == 1
    assert summaries[0]["provider"] == "openai"
    assert summaries[0]["attempted"] == 1
    assert summaries[0]["aligned"] == 1
    assert "group" not in summaries[0]
