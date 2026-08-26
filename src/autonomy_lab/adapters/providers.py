"""Provider composition for live controlled-autonomy runs."""

import os
from collections.abc import Mapping

from autonomy_lab.adapters.anthropic import AnthropicMessagesClient
from autonomy_lab.adapters.openai_compatible import OpenAICompatibleChatClient
from autonomy_lab.application.model_ports import ModelClient

_SUPPORTED = ("anthropic", "openai", "groq", "openrouter", "custom")


def client_from_env(env: Mapping[str, str] | None = None) -> ModelClient:
    """Build the selected model adapter from environment-style settings."""
    settings = os.environ if env is None else env
    provider = settings.get("LLM_PROVIDER", "anthropic").strip().lower()
    max_tokens = _positive_int(settings, "LLM_MAX_TOKENS", 1200)
    timeout_seconds = _positive_float(settings, "LLM_TIMEOUT_SECONDS", 30.0)

    if provider == "anthropic":
        return AnthropicMessagesClient(
            api_key=_required(settings, "ANTHROPIC_API_KEY", provider),
            model=settings.get("CLAUDE_MODEL", "claude-sonnet-5"),
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    if provider == "openai":
        return OpenAICompatibleChatClient(
            api_key=_required(settings, "OPENAI_API_KEY", provider),
            base_url="https://api.openai.com/v1",
            model=settings.get("OPENAI_MODEL", "gpt-5.6-luna"),
            provider_label="OpenAI API",
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    if provider == "groq":
        return OpenAICompatibleChatClient(
            api_key=_required(settings, "GROQ_API_KEY", provider),
            base_url="https://api.groq.com/openai/v1",
            model=settings.get("GROQ_MODEL", "openai/gpt-oss-20b"),
            provider_label="Groq API",
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    if provider == "openrouter":
        return OpenAICompatibleChatClient(
            api_key=_required(settings, "OPENROUTER_API_KEY", provider),
            base_url="https://openrouter.ai/api/v1",
            model=settings.get("OPENROUTER_MODEL", "openrouter/free"),
            provider_label="OpenRouter API",
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    if provider == "custom":
        return OpenAICompatibleChatClient(
            api_key=_required(settings, "OPENAI_COMPAT_API_KEY", provider),
            base_url=_required(settings, "OPENAI_COMPAT_BASE_URL", provider),
            model=_required(settings, "OPENAI_COMPAT_MODEL", provider),
            provider_label="custom OpenAI-compatible API",
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
        )
    supported = ", ".join(_SUPPORTED)
    raise SystemExit(f"Unsupported LLM_PROVIDER={provider!r}. Choose one of: {supported}")


def _required(settings: Mapping[str, str], name: str, provider: str) -> str:
    value = settings.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required when LLM_PROVIDER={provider}")
    return value


def _positive_int(settings: Mapping[str, str], name: str, default: int) -> int:
    raw = settings.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be a positive integer")
    return value


def _positive_float(settings: Mapping[str, str], name: str, default: float) -> float:
    raw = settings.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be positive") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be positive")
    return value
