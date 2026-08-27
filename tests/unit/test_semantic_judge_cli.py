import json

import pytest

import autonomy_lab.cli as base_cli
import autonomy_lab.semantic_judge_cli as judge_cli
from autonomy_lab.adapters.providers import ProviderSelection
from autonomy_lab.domain.autonomy import AutonomyPattern, ModelTurn, ModelUsage, PatternRun


class StaticRunner:
    def __init__(self, pattern: AutonomyPattern) -> None:
        self._pattern = pattern

    def run(self, incident_id: str) -> PatternRun:
        return PatternRun(
            pattern=self._pattern,
            incident_id=incident_id,
            answer="grounded answer",
            model_calls=2,
            tool_calls=0,
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
                '{"verdict":"unsupported-claim","rationale":"No bounded evidence supports '
                'this claim.","evidence_sources":[]}'
            ),
            usage=ModelUsage(7, 3),
        )


def _patch_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> StaticRunner:
        del store, model
        return StaticRunner(pattern)

    monkeypatch.setattr(base_cli, "_build_runner", build_runner)


def test_cross_model_calibration_exposes_generator_and_judge_identity(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_runner(monkeypatch)
    judge = StaticSemanticModel()
    monkeypatch.setattr(
        judge_cli,
        "configured_client_from_env",
        lambda: (
            object(),
            ProviderSelection("openai", "generator-model", 4000, 60.0),
        ),
    )
    monkeypatch.setattr(
        judge_cli,
        "semantic_client_from_env",
        lambda: (
            judge,
            ProviderSelection("groq", "judge-model", 600, 20.0),
        ),
    )

    assert judge_cli.main(["augmented", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["generator"]["provider"] == "openai"
    assert payload["generator"]["model"] == "generator-model"
    assert payload["judge"]["provider"] == "groq"
    assert payload["judge"]["model"] == "judge-model"
    assert payload["self_judge"] is False
    assert payload["model_calls"] == 2
    assert payload["semantic_claim_evaluation"]["semantic_model_calls"] == 1
    assert payload["semantic_claim_evaluation"]["semantic_input_tokens"] == 7
    assert judge.calls == 1


def test_same_generator_and_judge_is_marked_as_self_judge(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_runner(monkeypatch)
    selection = ProviderSelection("openai", "same-model", 4000, 60.0)
    monkeypatch.setattr(judge_cli, "configured_client_from_env", lambda: (object(), selection))
    monkeypatch.setattr(
        judge_cli,
        "semantic_client_from_env",
        lambda: (StaticSemanticModel(), selection),
    )

    assert judge_cli.main(["augmented", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["self_judge"] is True


def test_judge_configuration_failure_preserves_successful_generator_run(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_runner(monkeypatch)
    monkeypatch.setattr(
        judge_cli,
        "configured_client_from_env",
        lambda: (
            object(),
            ProviderSelection("openai", "generator-model", 4000, 60.0),
        ),
    )

    def fail_judge() -> object:
        raise SystemExit(
            "SEMANTIC_GROQ_API_KEY or GROQ_API_KEY is required when SEMANTIC_LLM_PROVIDER=groq"
        )

    monkeypatch.setattr(judge_cli, "semantic_client_from_env", fail_judge)

    assert judge_cli.main(["augmented", "--json"]) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["answer"] == "grounded answer"
    assert payload["model_calls"] == 2
    assert payload["generator"]["provider"] == "openai"
    assert payload["judge"] is None
    assert payload["semantic_claim_evaluation"]["status"] == "error"
    assert "configuration_error" in payload["semantic_claim_evaluation"]["error"]
