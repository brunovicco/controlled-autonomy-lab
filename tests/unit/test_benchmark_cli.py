import csv
import json
from pathlib import Path

import pytest

import autonomy_lab.cli as cli
from autonomy_lab.adapters.benchmark_metadata import BenchmarkEnvironment
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun


class StaticRunner:
    def __init__(self, pattern: AutonomyPattern) -> None:
        self._pattern = pattern

    def run(self, incident_id: str) -> PatternRun:
        return PatternRun(
            pattern=self._pattern,
            incident_id=incident_id,
            answer="grounded answer",
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


def _patch_benchmark_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rate_limit_pattern: AutonomyPattern | None = None,
) -> None:
    monkeypatch.setattr(cli, "_client_from_env", lambda: object())
    monkeypatch.setattr(
        cli,
        "benchmark_environment_from_env",
        lambda: BenchmarkEnvironment(
            provider="groq",
            model="openai/gpt-oss-20b",
            max_tokens=900,
            timeout_seconds=30.0,
            reasoning_effort="medium",
            git_commit="abc123",
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


def test_benchmark_command_writes_reproducible_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_benchmark_dependencies(monkeypatch)
    output = tmp_path / "benchmark"

    exit_code = cli.main(
        [
            "benchmark",
            "--incident",
            "INC-001",
            "--runs",
            "1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    stdout = capsys.readouterr().out
    assert "benchmark: complete" in stdout
    assert "groq" in stdout
    assert "abc123" in stdout

    records = [
        json.loads(line)
        for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == len(AutonomyPattern)
    assert all(record["status"] == "ok" for record in records)
    assert all("answer" not in record for record in records)

    with (output / "summary.csv").open(encoding="utf-8", newline="") as handle:
        summaries = list(csv.DictReader(handle))
    assert len(summaries) == len(AutonomyPattern)
    assert {row["pattern"] for row in summaries} == {pattern.value for pattern in AutonomyPattern}
    assert "Benchmark status: `complete`" in (output / "summary.md").read_text(encoding="utf-8")


def test_benchmark_command_persists_partial_results_and_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_benchmark_dependencies(monkeypatch, rate_limit_pattern=AutonomyPattern.CHAINING)
    output = tmp_path / "benchmark"

    exit_code = cli.main(["benchmark", "--runs", "1", "--output", str(output)])

    assert exit_code == 2
    assert "benchmark: partial" in capsys.readouterr().out
    records = [
        json.loads(line)
        for line in (output / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    chaining = next(record for record in records if record["pattern"] == "chaining")
    agent = next(record for record in records if record["pattern"] == "agent")
    assert chaining["status"] == "rate_limited"
    assert chaining["retry_after"] == "3"
    assert agent["status"] == "ok"
    assert "Benchmark status: `partial`" in (output / "summary.md").read_text(encoding="utf-8")
