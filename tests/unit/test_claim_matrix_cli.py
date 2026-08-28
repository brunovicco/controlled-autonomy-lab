import json

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from autonomy_lab import claim_matrix_cli


def test_claim_matrix_cli_emits_deterministic_json(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = claim_matrix_cli.main(["--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["claim_set"]["version"] == "v1"
    assert payload["claim_set"]["cases"] == 18
    assert payload["judge"] is None
    assert payload["semantic_error"] is None
    assert payload["summary"]["semantic_model_calls"] == 0
    assert len(payload["rows"]) == 18


def test_claim_matrix_cli_preserves_baseline_when_judge_config_is_invalid(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SEMANTIC_LLM_PROVIDER", "groq")
    monkeypatch.delenv("SEMANTIC_GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    exit_code = claim_matrix_cli.main(["--semantic", "--json"])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["deterministic_correct"] > 0
    assert payload["judge"] is None
    assert "GROQ_API_KEY" in payload["semantic_error"]
