"""Minimal OpenAI-compatible Chat Completions adapter using only the standard library."""

import http.client
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from harness_example.domain.agent import AgentMessage, AgentTurn, ToolCall, ToolResult, ToolSpec
from harness_example.domain.autonomy import ModelTurn, ModelUsage


class ModelProviderError(RuntimeError):
    """Raised when an OpenAI-compatible provider cannot return a valid turn."""


class OpenAICompatibleChatClient:
    """Synchronous adapter for OpenAI-compatible Chat Completions APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        provider_label: str = "OpenAI-compatible provider",
        max_tokens: int = 1200,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Configure a bounded HTTPS Chat Completions client."""
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        parsed = urlsplit(base_url.rstrip("/"))
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("base_url must be a plain HTTPS origin/path without credentials or query")

        self._api_key = api_key
        self._host = parsed.hostname
        self._port = parsed.port
        self._base_path = parsed.path.rstrip("/")
        self._model = model
        self._provider_label = provider_label
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        """Execute one bounded text-only Chat Completions call."""
        response = self._post(
            {
                "model": self._model,
                "max_completion_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            }
        )
        choice = self._first_choice(response)
        message = self._choice_message(choice)
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            raise ModelProviderError(f"{self._provider_label} response did not contain text")
        return ModelTurn(
            text=text.strip(),
            usage=self._extract_usage(response),
            stop_reason=str(choice.get("finish_reason") or "unknown"),
        )

    def next_turn(
        self,
        *,
        system: str,
        messages: tuple[AgentMessage, ...],
        tools: tuple[ToolSpec, ...],
    ) -> AgentTurn:
        """Execute one provider-neutral tool-use turn through Chat Completions."""
        api_messages: list[dict[str, object]] = [{"role": "system", "content": system}]
        for message in messages:
            api_messages.extend(self._message_to_api(message))

        response = self._post(
            {
                "model": self._model,
                "max_completion_tokens": self._max_tokens,
                "messages": api_messages,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": dict(tool.input_schema),
                        },
                    }
                    for tool in tools
                ],
                "tool_choice": "auto",
            }
        )
        choice = self._first_choice(response)
        message = self._choice_message(choice)
        text = message.get("content")
        tool_calls = self._extract_tool_calls(message)
        return AgentTurn(
            message=AgentMessage(
                role="assistant",
                text=text.strip() if isinstance(text, str) else "",
                tool_calls=tool_calls,
            ),
            usage=self._extract_usage(response),
            stop_reason=str(choice.get("finish_reason") or "unknown"),
        )

    def _post(self, body: Mapping[str, object]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        connection = http.client.HTTPSConnection(
            self._host,
            port=self._port,
            timeout=self._timeout_seconds,
        )
        try:
            connection.request(
                "POST",
                f"{self._base_path}/chat/completions",
                body=payload,
                headers={
                    "authorization": f"Bearer {self._api_key}",
                    "content-type": "application/json",
                },
            )
            response = connection.getresponse()
            raw = response.read()
        except (OSError, http.client.HTTPException) as exc:
            raise ModelProviderError(f"{self._provider_label} request failed") from exc
        finally:
            connection.close()

        if response.status < 200 or response.status >= 300:
            raise ModelProviderError(f"{self._provider_label} returned HTTP {response.status}")
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelProviderError(f"{self._provider_label} returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError(f"{self._provider_label} response must be a JSON object")
        return decoded

    def _first_choice(self, response: Mapping[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ModelProviderError(f"{self._provider_label} response is missing choices")
        return choices[0]

    def _choice_message(self, choice: Mapping[str, Any]) -> dict[str, Any]:
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelProviderError(f"{self._provider_label} response is missing message")
        return message

    def _extract_tool_calls(self, message: Mapping[str, Any]) -> tuple[ToolCall, ...]:
        raw_calls = message.get("tool_calls")
        if raw_calls is None:
            return ()
        if not isinstance(raw_calls, list):
            raise ModelProviderError(f"{self._provider_label} returned malformed tool_calls")

        calls: list[ToolCall] = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                raise ModelProviderError(f"{self._provider_label} returned malformed tool call")
            call_id = raw_call.get("id")
            function = raw_call.get("function")
            if not isinstance(call_id, str) or not isinstance(function, dict):
                raise ModelProviderError(f"{self._provider_label} returned malformed tool metadata")
            name = function.get("name")
            arguments_json = function.get("arguments")
            if not isinstance(name, str) or not isinstance(arguments_json, str):
                raise ModelProviderError(f"{self._provider_label} returned malformed function call")
            try:
                arguments = json.loads(arguments_json)
            except json.JSONDecodeError as exc:
                raise ModelProviderError(
                    f"{self._provider_label} returned invalid tool arguments JSON"
                ) from exc
            if not isinstance(arguments, dict):
                raise ModelProviderError(
                    f"{self._provider_label} tool arguments must be a JSON object"
                )
            calls.append(ToolCall(call_id=call_id, name=name, arguments=arguments))
        return tuple(calls)

    @staticmethod
    def _extract_usage(response: Mapping[str, Any]) -> ModelUsage:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return ModelUsage()
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        return ModelUsage(
            input_tokens=input_tokens if isinstance(input_tokens, int) else 0,
            output_tokens=output_tokens if isinstance(output_tokens, int) else 0,
        )

    @staticmethod
    def _message_to_api(message: AgentMessage) -> list[dict[str, object]]:
        if message.role == "user":
            return [{"role": "user", "content": message.text}]
        if message.role == "assistant":
            payload: dict[str, object] = {"role": "assistant", "content": message.text or None}
            if message.tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": call.call_id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(dict(call.arguments), separators=(",", ":")),
                        },
                    }
                    for call in message.tool_calls
                ]
            return [payload]
        return [OpenAICompatibleChatClient._tool_result_to_api(result) for result in message.tool_results]

    @staticmethod
    def _tool_result_to_api(result: ToolResult) -> dict[str, object]:
        content = f"ERROR: {result.content}" if result.is_error else result.content
        return {
            "role": "tool",
            "tool_call_id": result.call_id,
            "content": content,
        }
