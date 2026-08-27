"""Provider composition for live controlled-autonomy runs."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from autonomy_lab.adapters.anthropic import AnthropicMessagesClient
from autonomy_lab.adapters.openai_compatible import OpenAICompatibleChatClient
from autonomy_lab.adapters.openai_responses import OpenAIResponsesClient
from autonomy_lab.application.model_ports import ModelClient

_SUPPORTED = ("anthropic", "openai", "groq", "openrouter", "custom")
_MODEL_SETTINGS = {
    "anthropic": ("CLAUDE_MODEL", "claude-sonnet-5"),
    "openai": ("OPENAI_MODEL", "gpt-5.6-luna"),
    "groq": ("GROQ_MODEL", "openai/gpt-oss-20b"),
    "openrouter": ("OPENROUTER_MODEL", "openrouter/free"),
}


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    """Resolved provider identity and bounded runtime limits."""

    provider: str
    model: str
    max_tokens: int
    timeout_seconds: float


def client_from_env(env: Mapping[str, str] | None = None) -> ModelClient:
    """Build the selected generator model adapter from environment-style settings."""
    client, _ = configured_client_from_env(env)
    return client


def configured_client_from_env(
    env: Mapping[str, str] | None = None,
    *,
    namespace: str = "",
) -> tuple[ModelClient, ProviderSelection]:
    """Build one provider client and expose its resolved non-secret runtime identity.

    ``namespace="SEMANTIC_"`` creates an independently configurable semantic judge.
    Namespaced values fall back to the corresponding generator/provider values when omitted.
    """
    settings = os.environ if env is None else env
    provider = _setting(settings, "LLM_PROVIDER", namespace=namespace, default="anthropic")
    provider = provider.strip().lower()
    max_tokens = _positive_int(
        settings,
        "LLM_MAX_TOKENS",
        1200,
        namespace=namespace,
    )
    timeout_seconds = _positive_float(
        settings,
        "LLM_TIMEOUT_SECONDS",
        30.0,
        namespace=namespace,
    )

    if provider == "custom":
        model = _required(settings, "OPENAI_COMPAT_MODEL", provider, namespace=namespace)
    else:
        model_name, default_model = _MODEL_SETTINGS.get(provider, ("", ""))
        model = _setting(settings, model_name, namespace=namespace, default=default_model)

    selection = ProviderSelection(
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )

    if provider == "anthropic":
        return (
            AnthropicMessagesClient(
                api_key=_required(settings, "ANTHROPIC_API_KEY", provider, namespace=namespace),
                model=model,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ),
            selection,
        )
    if provider == "openai":
        return (
            OpenAIResponsesClient(
                api_key=_required(settings, "OPENAI_API_KEY", provider, namespace=namespace),
                model=model,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ),
            selection,
        )
    if provider == "groq":
        return (
            OpenAICompatibleChatClient(
                api_key=_required(settings, "GROQ_API_KEY", provider, namespace=namespace),
                base_url="https://api.groq.com/openai/v1",
                model=model,
                provider_label="Groq API",
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ),
            selection,
        )
    if provider == "openrouter":
        return (
            OpenAICompatibleChatClient(
                api_key=_required(settings, "OPENROUTER_API_KEY", provider, namespace=namespace),
                base_url="https://openrouter.ai/api/v1",
                model=model,
                provider_label="OpenRouter API",
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ),
            selection,
        )
    if provider == "custom":
        return (
            OpenAICompatibleChatClient(
                api_key=_required(settings, "OPENAI_COMPAT_API_KEY", provider, namespace=namespace),
                base_url=_required(
                    settings,
                    "OPENAI_COMPAT_BASE_URL",
                    provider,
                    namespace=namespace,
                ),
                model=model,
                provider_label="custom OpenAI-compatible API",
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            ),
            selection,
        )
    supported = ", ".join(_SUPPORTED)
    variable = f"{namespace}LLM_PROVIDER"
    raise SystemExit(f"Unsupported {variable}={provider!r}. Choose one of: {supported}")


def semantic_client_from_env(
    env: Mapping[str, str] | None = None,
) -> tuple[ModelClient, ProviderSelection]:
    """Build the semantic judge, falling back to generator settings when not overridden."""
    return configured_client_from_env(env, namespace="SEMANTIC_")


def _setting(
    settings: Mapping[str, str],
    name: str,
    *,
    namespace: str,
    default: str,
) -> str:
    if namespace:
        namespaced = settings.get(f"{namespace}{name}")
        if namespaced is not None:
            return namespaced
    return settings.get(name, default)


def _required(
    settings: Mapping[str, str],
    name: str,
    provider: str,
    *,
    namespace: str = "",
) -> str:
    if namespace:
        namespaced_name = f"{namespace}{name}"
        value = settings.get(namespaced_name, "").strip()
        if value:
            return value
    value = settings.get(name, "").strip()
    if value:
        return value
    provider_name = f"{namespace}LLM_PROVIDER" if namespace else "LLM_PROVIDER"
    if namespace:
        raise SystemExit(
            f"{namespace}{name} or {name} is required when {provider_name}={provider}"
        )
    raise SystemExit(f"{name} is required when {provider_name}={provider}")


def _raw_setting(
    settings: Mapping[str, str],
    name: str,
    *,
    namespace: str,
) -> str | None:
    if namespace:
        namespaced = settings.get(f"{namespace}{name}")
        if namespaced is not None:
            return namespaced
    return settings.get(name)


def _positive_int(
    settings: Mapping[str, str],
    name: str,
    default: int,
    *,
    namespace: str = "",
) -> int:
    raw = _raw_setting(settings, name, namespace=namespace)
    if raw is None:
        return default
    display_name = f"{namespace}{name}" if namespace and f"{namespace}{name}" in settings else name
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{display_name} must be a positive integer") from exc
    if value <= 0:
        raise SystemExit(f"{display_name} must be a positive integer")
    return value


def _positive_float(
    settings: Mapping[str, str],
    name: str,
    default: float,
    *,
    namespace: str = "",
) -> float:
    raw = _raw_setting(settings, name, namespace=namespace)
    if raw is None:
        return default
    display_name = f"{namespace}{name}" if namespace and f"{namespace}{name}" in settings else name
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{display_name} must be positive") from exc
    if value <= 0:
        raise SystemExit(f"{display_name} must be positive")
    return value
