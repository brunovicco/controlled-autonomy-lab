import json
from pathlib import Path

import pytest

import autonomy_lab.epistemic_benchmark_cli as cli
from autonomy_lab.adapters.benchmark_metadata import BenchmarkEnvironment
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun
from autonomy_lab.domain.benchmark import (
    BENCHMARK_RECORD_SCHEMA_VERSION,
    BREADTH_MANIFEST_SCHEMA_VERSION,
    EPISTEMIC_EVALUATION_VERSION,
)


class StaticRunner:
    def __init__(self, pattern: AutonomyPattern) -> None:
        self._pattern = pattern

    def run(self, incident_id: str) -> PatternRun:
        return PatternRun(
            pattern=self._pattern,
            incident_id=incident_id,
            answer="Observed evidence does not establish a causal conclusion.",
            model_calls=2,
            tool_calls=1 if self._pattern is AutonomyPattern.AGENT else 0,
            steps=("inspect", "final-answer"),
            usage=ModelUsage(20, 5),
            latency_ms=12.5,
        )


class RateLimitedRunner:
    def run(self, incident_id: str) -> PatternRun:
        del incident_id
        raise ModelRateLimitError("Groq API returned HTTP 429", retry_after="3")


def _patch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rate_limit_pattern: AutonomyPattern | None = None,
) -> None:
    monkeypatch.setattr(cli, "client_from_env", lambda: object())
    monkeypatch.setattr(
        cli,
        "benchmark_environment_from_env",
        lambda: BenchmarkEnvironment(
            provider="groq",
            model="openai/gpt-oss-20b",
            max_tokens=900,
            timeout_seconds=30.0,
            reasoning_effort="medium",
            git_commit="epistemic-freeze",
        ),
    )

    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> StaticRunner | RateLimitedRunner:
        del store, model
        if pattern is rate_limit_pattern:
            return RateLimitedRunner()
        return StaticRunner(pattern)

    monkeypatch.setattr(cli, "_build_runner", build_runner)


def test_epistemic_breadth_runner_writes_new_generation_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dependencies(monkeypatch)
    output = tmp_path / "breadth-v2"

    exit_code = cli.main(
        [
            "--all-incidents",
            "--runs",
            "1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    manifest = json.loads((output / "breadth-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == BREADTH_MANIFEST_SCHEMA_VERSION
    assert manifest["record_schema_version"] == BENCHMARK_RECORD_SCHEMA_VERSION
    assert manifest["epistemic_evaluation_version"] == EPISTEMIC_EVALUATION_VERSION
    assert manifest["attempted"] == 24
    assert manifest["completed"] == 24
    assert manifest["epistemic_evaluated"] == 24
    assert manifest["bound_exceeded"] == 0
    assert "do not append" in manifest["generation_boundary"]

    postures: dict[str, str] = {}
    for incident_id in manifest["incidents"]:
        records = [
            json.loads(line)
            for line in (output / incident_id / "runs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert len(records) == len(AutonomyPattern)
        assert all(
            record["schema_version"] == BENCHMARK_RECORD_SCHEMA_VERSION
            for record in records
        )
        assert all(
            record["epistemic_evaluation_version"] == EPISTEMIC_EVALUATION_VERSION
            for record in records
        )
        assert all(record["epistemic_verdict"] is not None for record in records)
        assert all("answer" not in record for record in records)
        postures[incident_id] = records[0]["epistemic_expected_posture"]

    assert postures == {
        "INC-001": "correlational",
        "INC-002": "confirmed-cause",
        "INC-003": "confirmed-cause",
        "INC-004": "inconclusive",
    }


def test_epistemic_breadth_runner_keeps_rate_limit_as_availability_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_dependencies(monkeypatch, rate_limit_pattern=AutonomyPattern.CHAINING)
    output = tmp_path / "breadth-v2"

    exit_code = cli.main(
        [
            "--all-incidents",
            "--runs",
            "1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    manifest = json.loads((output / "breadth-manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "partial"
    assert manifest["rate_limited"] == 4
    assert manifest["completed"] == 20
    assert manifest["epistemic_evaluated"] == 20

    inc001 = [
        json.loads(line)
        for line in (output / "INC-001" / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    chaining = next(record for record in inc001 if record["pattern"] == "chaining")
    assert chaining["status"] == "rate_limited"
    assert chaining["epistemic_evaluation_version"] == EPISTEMIC_EVALUATION_VERSION
    assert chaining["epistemic_verdict"] is None
