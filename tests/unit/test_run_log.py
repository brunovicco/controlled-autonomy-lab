import json
from pathlib import Path

from harness_example.adapters.run_log import MetadataRunRecorder
from harness_example.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun


def test_run_log_records_metrics_but_not_answer_content(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "runs.jsonl"
    run = PatternRun(
        pattern=AutonomyPattern.AGENT,
        incident_id="INC-001",
        answer="sensitive model answer must not be logged",
        model_calls=3,
        tool_calls=2,
        steps=("get_service_metrics", "final-answer"),
        usage=ModelUsage(100, 20),
        latency_ms=42.1234,
    )

    MetadataRunRecorder(path).append(run)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pattern"] == "agent"
    assert payload["model_calls"] == 3
    assert payload["steps"] == ["get_service_metrics", "final-answer"]
    assert "answer" not in payload
    assert "sensitive" not in path.read_text(encoding="utf-8")
