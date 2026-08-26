import json

import pytest

import autonomy_lab.cli as cli
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.autonomy import AutonomyPattern, PatternRun


class RateLimitedRunner:
    def run(self, incident_id: str) -> PatternRun:
        del incident_id
        raise ModelRateLimitError("Groq API returned HTTP 429", retry_after="7")


def _patch_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_client_from_env", lambda: object())

    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> RateLimitedRunner:
        del pattern, store, model
        return RateLimitedRunner()

    monkeypatch.setattr(cli, "_build_runner", build_runner)


def test_run_json_returns_structured_rate_limit_without_traceback(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rate_limit(monkeypatch)

    assert cli.main(["run", "agent", "--incident", "INC-001", "--json"]) == 2

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert captured.err == ""
    assert payload == {
        "pattern": "agent",
        "incident_id": "INC-001",
        "status": "rate_limited",
        "error": "Groq API returned HTTP 429",
        "retry_after": "7",
    }


def test_run_human_returns_rate_limit_on_stderr(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rate_limit(monkeypatch)

    assert cli.main(["run", "agent", "--incident", "INC-001"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "pattern: agent" in captured.err
    assert "status:  rate_limited" in captured.err
    assert "Groq API returned HTTP 429" in captured.err
    assert "retry after: 7" in captured.err
