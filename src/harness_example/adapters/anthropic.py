"""Minimal Claude Messages API adapter with no third-party SDK dependency."""

import http.client
import json
from collections.abc import Mapping
from typing import Any

from harness_example.domain.autonomy import ModelTurn, ModelUsage

_API_HOST = "api.anthropic.com"
_API_PATH = "/v1/messages"
_API_VERSION = "2023-06-01"


class ModelProviderError(RuntimeError):
    """Raised when the external model provider cannot return a valid turn."""


class AnthropicMessagesClient:
    """Small synchronous adapter around Anthropic's Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-5",
        max_tokens: int = 1200,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Configure a bounded Claude API client."""
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        """Execute one bounded text-only Messages API call."""
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = self._post(body)
        return ModelTurn(
            text=self._extract_text(response),
            usage=self._extract_usage(response),
            stop_reason=str(response.get("stop_reason") or "unknown"),
        )

    def _post(self, body: Mapping[str, object]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        connection = http.client.HTTPSConnection(_API_HOST, timeout=self._timeout_seconds)
        try:
            connection.request(
                "POST",
                _API_PATH,
                body=payload,
                headers={
                    "anthropic-version": _API_VERSION,
                    "content-type": "application/json",
                    "x-api-key": self._api_key,
                },
            )
            response = connection.getresponse()
            raw = response.read()
        except (OSError, http.client.HTTPException) as exc:
            raise ModelProviderError("Claude API request failed") from exc
        finally:
            connection.close()

        if response.status < 200 or response.status >= 300:
            raise ModelProviderError(f"Claude API returned HTTP {response.status}")
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelProviderError("Claude API returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError("Claude API response must be a JSON object")
        return decoded

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        content = response.get("content")
        if not isinstance(content, list):
            raise ModelProviderError("Claude API response is missing content")
        chunks = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(chunk for chunk in chunks if isinstance(chunk, str)).strip()
        if not text:
            raise ModelProviderError("Claude API response did not contain text")
        return text

    @staticmethod
    def _extract_usage(response: Mapping[str, Any]) -> ModelUsage:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return ModelUsage()
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        return ModelUsage(
            input_tokens=input_tokens if isinstance(input_tokens, int) else 0,
            output_tokens=output_tokens if isinstance(output_tokens, int) else 0,
        )
