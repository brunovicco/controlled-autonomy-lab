from pathlib import Path

from autonomy_lab.adapters.benchmark_metadata import benchmark_environment_from_env


def test_benchmark_metadata_uses_non_secret_provider_settings(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    ref = git_dir / "refs" / "heads" / "main"
    ref.parent.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ref.write_text("abc123\n", encoding="utf-8")

    environment = benchmark_environment_from_env(
        {
            "LLM_PROVIDER": "groq",
            "GROQ_MODEL": "openai/gpt-oss-20b",
            "GROQ_API_KEY": "must-not-be-recorded",
            "LLM_MAX_TOKENS": "900",
            "LLM_TIMEOUT_SECONDS": "45",
            "LLM_REASONING_EFFORT": "low",
        },
        repository_root=tmp_path,
    )

    assert environment.provider == "groq"
    assert environment.model == "openai/gpt-oss-20b"
    assert environment.max_tokens == 900
    assert environment.timeout_seconds == 45.0
    assert environment.reasoning_effort == "low"
    assert environment.git_commit == "abc123"
    assert "must-not-be-recorded" not in repr(environment)


def test_benchmark_metadata_prefers_explicit_commit(tmp_path: Path) -> None:
    environment = benchmark_environment_from_env(
        {
            "LLM_PROVIDER": "openrouter",
            "OPENROUTER_MODEL": "openrouter/free",
            "AUTONOMY_LAB_GIT_COMMIT": "def456",
        },
        repository_root=tmp_path,
    )

    assert environment.git_commit == "def456"
    assert environment.model == "openrouter/free"
