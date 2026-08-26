import json
from pathlib import Path

import pytest

import autonomy_lab.cli as cli
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelTurn, ModelUsage, PatternRun


class StaticRunner:
    def __init__(self, pattern: AutonomyPattern) -> None:
        self._pattern = pattern
        self.calls = 0

    def run(self, incident_id: str) -> PatternRun:
        self.calls += 1
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


class StaticSemanticModel:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        assert "bounded semantic support classifier" in system
        assert '"claim":"grounded answer"' in prompt
        self.calls += 1
        return ModelTurn(
            text=(
                '{"verdict":"unsupported-claim","rationale":"No bounded evidence directly '
                'supports this claim.","evidence_sources":[]}'
            ),
            usage=ModelUsage(7, 3),
        )


class RateLimitedRunner:
    def run(self, incident_id: str) -> PatternRun:
        del incident_id
        raise ModelRateLimitError("Groq API returned HTTP 429", retry_after="7")


def _patch_live_dependencies(monkeypatch: pytest.MonkeyPatch) -> StaticSemanticModel:
    semantic_model = StaticSemanticModel()
    monkeypatch.setattr(cli, "_client_from_env", lambda: semantic_model)

    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> StaticRunner:
        del store, model
        return StaticRunner(pattern)

    monkeypatch.setattr(cli, "_build_runner", build_runner)
    return semantic_model


def test_client_from_env_requires_selected_provider_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        cli._client_from_env()


def test_run_command_supports_json_and_metadata_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)
    trace_file = tmp_path / "runs.jsonl"

    exit_code = cli.main(
        [
            "--trace-file",
            str(trace_file),
            "run",
            "augmented",
            "--incident",
            "INC-001",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pattern"] == "augmented"
    assert payload["answer"] == "grounded answer"
    assert "grounding" not in payload
    assert "claim_evaluation" not in payload
    assert "semantic_claim_evaluation" not in payload
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert "answer" not in trace


def test_run_command_can_emit_grounding_report_in_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    assert cli.main(["run", "augmented", "--grounding", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    grounding = payload["grounding"]
    assert grounding["unsupported_specifics"] == []
    assert grounding["proposed_specifics"] == []
    assert grounding["causality_overclaims"] == []
    assert grounding["specific_grounding_ratio"] == 1.0


def test_run_command_can_emit_claim_evaluation_in_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    assert cli.main(["run", "augmented", "--claims", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    claims = payload["claim_evaluation"]
    assert claims["supported_facts"] == 0
    assert claims["supported_inferences"] == 0
    assert claims["proposed_actions"] == 0
    assert claims["unsupported_claims"] == 1
    assert claims["evaluable_claims"] == 1
    assert claims["support_ratio"] == 0.0
    assert claims["claims"][0]["kind"] == "unsupported-claim"


def test_run_semantic_claims_implies_claims_and_keeps_usage_separate(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic_model = _patch_live_dependencies(monkeypatch)

    assert cli.main(["run", "augmented", "--semantic-claims", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["model_calls"] == 2
    assert payload["input_tokens"] == 20
    assert payload["output_tokens"] == 5
    assert "claim_evaluation" in payload

    semantic = payload["semantic_claim_evaluation"]
    assert semantic["status"] == "ok"
    assert semantic["semantic_model_calls"] == 1
    assert semantic["semantic_input_tokens"] == 7
    assert semantic["semantic_output_tokens"] == 3
    assert semantic["unsupported_claims"] == 1
    assert semantic["disagreements"] == 0
    assert semantic["claims"][0]["final_kind"] == "unsupported-claim"
    assert semantic_model.calls == 1


def test_semantic_claims_do_not_expand_metadata_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)
    trace_file = tmp_path / "semantic-runs.jsonl"

    exit_code = cli.main(
        [
            "--trace-file",
            str(trace_file),
            "run",
            "augmented",
            "--semantic-claims",
            "--json",
        ]
    )

    assert exit_code == 0
    json.loads(capsys.readouterr().out)
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    assert "answer" not in trace
    assert "claim_evaluation" not in trace
    assert "semantic_claim_evaluation" not in trace
    assert "semantic_model_calls" not in trace


def test_semantic_claim_failure_returns_partial_without_losing_run(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    def fail_semantic(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise cli.SemanticClaimEvaluationError("semantic evaluator returned invalid JSON")

    monkeypatch.setattr(cli, "_semantic_claim_evaluation_for_run", fail_semantic)

    assert cli.main(["run", "augmented", "--semantic-claims", "--json"]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["answer"] == "grounded answer"
    assert payload["model_calls"] == 2
    assert payload["semantic_claim_evaluation"]["status"] == "error"
    assert "invalid_semantic_output" in payload["semantic_claim_evaluation"]["error"]


def test_run_command_supports_human_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    assert cli.main(["run", "agent", "--grounding", "--claims"]) == 0

    output = capsys.readouterr().out
    assert "pattern:       agent" in output
    assert "trajectory:    inspect -> final-answer" in output
    assert "grounded answer" in output
    assert "grounding:" in output
    assert "unsupported specifics: 0" in output
    assert "proposed parameters:   0" in output
    assert "claim evaluation v2:" in output
    assert "unsupported claims:    1" in output


def test_compare_runs_every_pattern_with_grounding_columns(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    assert cli.main(["compare", "--incident", "INC-001"]) == 0

    output = capsys.readouterr().out
    assert "unsupported | proposed | causality | uncertainty | status" in output
    for pattern in AutonomyPattern:
        assert pattern.value in output
    assert output.count("| ok") == len(AutonomyPattern)


def test_compare_continues_after_rate_limit_and_returns_partial_status(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_client_from_env", lambda: object())

    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> StaticRunner | RateLimitedRunner:
        del store, model
        if pattern is AutonomyPattern.CHAINING:
            return RateLimitedRunner()
        return StaticRunner(pattern)

    monkeypatch.setattr(cli, "_build_runner", build_runner)

    assert cli.main(["compare", "--incident", "INC-001"]) == 2

    output = capsys.readouterr().out
    assert "chaining | - | - | - | - | - | - | - | - | - | rate_limited" in output
    assert "agent | 2 | 1" in output
    assert "| ok" in output


def test_repeat_reports_trajectory_variance(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_live_dependencies(monkeypatch)

    assert cli.main(["repeat", "agent", "--runs", "2"]) == 0

    output = capsys.readouterr().out
    assert "runs=2" in output
    assert "unique_trajectories=1" in output
    assert "run 1: inspect -> final-answer" in output
