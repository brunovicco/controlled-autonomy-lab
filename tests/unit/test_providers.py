import pytest

from autonomy_lab.adapters.anthropic import AnthropicMessagesClient
from autonomy_lab.adapters.openai_compatible import OpenAICompatibleChatClient
from autonomy_lab.adapters.openai_responses import OpenAIResponsesClient
from autonomy_lab.adapters.providers import (
    ProviderSelection,
    client_from_env,
    configured_client_from_env,
    semantic_client_from_env,
)


def test_anthropic_is_preserved_as_default_provider() -> None:
    client = client_from_env({"ANTHROPIC_API_KEY": "key"})

    assert isinstance(client, AnthropicMessagesClient)


def test_openai_uses_native_responses_api() -> None:
    client = client_from_env({"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key"})

    assert isinstance(client, OpenAIResponsesClient)


@pytest.mark.parametrize(
    ("provider", "key_name"),
    [
        ("groq", "GROQ_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ],
)
def test_openai_compatible_provider_presets(provider: str, key_name: str) -> None:
    client = client_from_env({"LLM_PROVIDER": provider, key_name: "key"})

    assert isinstance(client, OpenAICompatibleChatClient)


def test_custom_openai_compatible_provider() -> None:
    client = client_from_env(
        {
            "LLM_PROVIDER": "custom",
            "OPENAI_COMPAT_API_KEY": "key",
            "OPENAI_COMPAT_BASE_URL": "https://llm.example/v1",
            "OPENAI_COMPAT_MODEL": "example-model",
        }
    )

    assert isinstance(client, OpenAICompatibleChatClient)


def test_configured_client_exposes_non_secret_identity() -> None:
    client, selection = configured_client_from_env(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "secret",
            "OPENAI_MODEL": "generator-model",
            "LLM_MAX_TOKENS": "2000",
            "LLM_TIMEOUT_SECONDS": "45",
        }
    )

    assert isinstance(client, OpenAIResponsesClient)
    assert selection == ProviderSelection(
        provider="openai",
        model="generator-model",
        max_tokens=2000,
        timeout_seconds=45.0,
    )
    assert "secret" not in repr(selection)


def test_semantic_judge_can_use_different_provider_and_model() -> None:
    client, selection = semantic_client_from_env(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "generator-key",
            "OPENAI_MODEL": "generator-model",
            "SEMANTIC_LLM_PROVIDER": "groq",
            "GROQ_API_KEY": "judge-key",
            "GROQ_MODEL": "default-groq-model",
            "SEMANTIC_GROQ_MODEL": "judge-model",
            "SEMANTIC_LLM_MAX_TOKENS": "600",
            "SEMANTIC_LLM_TIMEOUT_SECONDS": "20",
        }
    )

    assert isinstance(client, OpenAICompatibleChatClient)
    assert selection == ProviderSelection(
        provider="groq",
        model="judge-model",
        max_tokens=600,
        timeout_seconds=20.0,
    )


def test_semantic_judge_defaults_to_generator_configuration() -> None:
    client, selection = semantic_client_from_env(
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "key",
            "OPENAI_MODEL": "same-model",
            "LLM_MAX_TOKENS": "2500",
            "LLM_TIMEOUT_SECONDS": "40",
        }
    )

    assert isinstance(client, OpenAIResponsesClient)
    assert selection == ProviderSelection(
        provider="openai",
        model="same-model",
        max_tokens=2500,
        timeout_seconds=40.0,
    )


def test_semantic_judge_can_use_namespaced_key_without_generator_key() -> None:
    client, selection = semantic_client_from_env(
        {
            "LLM_PROVIDER": "groq",
            "SEMANTIC_LLM_PROVIDER": "openai",
            "SEMANTIC_OPENAI_API_KEY": "judge-only-key",
            "SEMANTIC_OPENAI_MODEL": "judge-model",
        }
    )

    assert isinstance(client, OpenAIResponsesClient)
    assert selection.provider == "openai"
    assert selection.model == "judge-model"


def test_selected_provider_requires_its_own_key() -> None:
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        client_from_env({"LLM_PROVIDER": "openrouter"})


def test_semantic_provider_missing_key_fails_with_semantic_context() -> None:
    with pytest.raises(SystemExit, match="SEMANTIC_GROQ_API_KEY or GROQ_API_KEY"):
        semantic_client_from_env(
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "generator-key",
                "SEMANTIC_LLM_PROVIDER": "groq",
            }
        )


def test_unknown_provider_fails_closed() -> None:
    with pytest.raises(SystemExit, match="Unsupported LLM_PROVIDER"):
        client_from_env({"LLM_PROVIDER": "unknown"})


def test_unknown_semantic_provider_fails_closed() -> None:
    with pytest.raises(SystemExit, match="Unsupported SEMANTIC_LLM_PROVIDER"):
        semantic_client_from_env(
            {
                "ANTHROPIC_API_KEY": "key",
                "SEMANTIC_LLM_PROVIDER": "unknown",
            }
        )


def test_invalid_live_limits_fail_closed() -> None:
    with pytest.raises(SystemExit, match="LLM_MAX_TOKENS"):
        client_from_env({"ANTHROPIC_API_KEY": "key", "LLM_MAX_TOKENS": "0"})
    with pytest.raises(SystemExit, match="LLM_TIMEOUT_SECONDS"):
        client_from_env({"ANTHROPIC_API_KEY": "key", "LLM_TIMEOUT_SECONDS": "not-a-number"})


def test_invalid_semantic_limits_fail_closed() -> None:
    with pytest.raises(SystemExit, match="SEMANTIC_LLM_MAX_TOKENS"):
        semantic_client_from_env(
            {
                "ANTHROPIC_API_KEY": "key",
                "SEMANTIC_LLM_MAX_TOKENS": "0",
            }
        )
