import pytest

from autonomy_lab.adapters.anthropic import AnthropicMessagesClient
from autonomy_lab.adapters.openai_compatible import OpenAICompatibleChatClient
from autonomy_lab.adapters.providers import client_from_env


def test_anthropic_is_preserved_as_default_provider() -> None:
    client = client_from_env({"ANTHROPIC_API_KEY": "key"})

    assert isinstance(client, AnthropicMessagesClient)


@pytest.mark.parametrize(
    ("provider", "key_name"),
    [
        ("openai", "OPENAI_API_KEY"),
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


def test_selected_provider_requires_its_own_key() -> None:
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        client_from_env({"LLM_PROVIDER": "openrouter"})


def test_unknown_provider_fails_closed() -> None:
    with pytest.raises(SystemExit, match="Unsupported LLM_PROVIDER"):
        client_from_env({"LLM_PROVIDER": "unknown"})


def test_invalid_live_limits_fail_closed() -> None:
    with pytest.raises(SystemExit, match="LLM_MAX_TOKENS"):
        client_from_env({"ANTHROPIC_API_KEY": "key", "LLM_MAX_TOKENS": "0"})
    with pytest.raises(SystemExit, match="LLM_TIMEOUT_SECONDS"):
        client_from_env({"ANTHROPIC_API_KEY": "key", "LLM_TIMEOUT_SECONDS": "not-a-number"})
