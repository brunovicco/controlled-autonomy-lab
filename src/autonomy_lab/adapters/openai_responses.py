"""Native OpenAI Responses API adapter with stateless reasoning preservation."""

import http.client
import json
from collections.abc import Mapping
from typing import Any

from autonomy_lab.adapters.provider_error_detail import safe_provider_error_detail
from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.domain.agent import AgentMessage, AgentTurn, ToolCall, ToolResult, ToolSpec
from autonomy_lab.domain.autonomy import ModelTurn, ModelUsage

_API_HOST = "api.openai.com"
_API_PATH = "/v1/responses"


class OpenAIResponsesClient:
    """Synchronous OpenAI Responses client with in-memory stateless tool context."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-luna",
        max_tokens: int = 1200,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Configure a bounded Responses API client."""
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._agent_history: list[dict[str, Any]] = []
        self._seen_tool_results: set[str] = set()

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        """Execute one bounded text-only Responses API call."""
        response = self._post(
            {
                "model": self._model,
                "store": False,
                "max_output_tokens": self._max_tokens,
                "instructions": system,
                "input": [{"role": "user", "content": prompt}],
            }
        )
        text = self._extract_text(response)
        stop_reason = self._stop_reason(response)
        if not text:
            raise ModelProviderError(
                f"OpenAI Responses API response did not contain text; stop_reason={stop_reason}"
            )
        return ModelTurn(
            text=text,
            usage=self._extract_usage(response),
            stop_reason=stop_reason,
        )

    def next_turn(
        self,
        *,
        system: str,
        messages: tuple[AgentMessage, ...],
        tools: tuple[ToolSpec, ...],
    ) -> AgentTurn:
        """Execute one Responses tool-use turn while preserving opaque reasoning items."""
        if len(messages) == 1 and messages[0].role == "user":
            self._agent_history = [{"role": "user", "content": messages[0].text}]
            self._seen_tool_results.clear()
        elif not self._agent_history:
            self._agent_history = self._visible_input(messages)

        self._append_new_tool_results(messages)
        response = self._post(
            {
                "model": self._model,
                "store": False,
                "max_output_tokens": self._max_tokens,
                "instructions": system,
                "input": self._agent_history,
                "tools": [self._tool_to_api(tool) for tool in tools],
                "tool_choice": "auto",
            }
        )
        output = response.get("output")
        if not isinstance(output, list):
            raise ModelProviderError("OpenAI Responses API response is missing output")
        safe_output = [item for item in output if isinstance(item, dict)]
        self._agent_history.extend(safe_output)

        return AgentTurn(
            message=AgentMessage(
                role="assistant",
                text=self._extract_text(response),
                tool_calls=self._extract_tool_calls(response),
            ),
            usage=self._extract_usage(response),
            stop_reason=self._stop_reason(response),
        )

    def _append_new_tool_results(self, messages: tuple[AgentMessage, ...]) -> None:
        for message in messages:
            if message.role != "tool":
                continue
            for result in message.tool_results:
                if result.call_id in self._seen_tool_results:
                    continue
                self._agent_history.append(self._tool_result_to_api(result))
                self._seen_tool_results.add(result.call_id)

    @staticmethod
    def _visible_input(messages: tuple[AgentMessage, ...]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "user":
                history.append({"role": "user", "content": message.text})
            elif message.role == "assistant":
                if message.text:
                    history.append({"role": "assistant", "content": message.text})
                history.extend(
                    {
                        "type": "function_call",
                        "call_id": call.call_id,
                        "name": call.name,
                        "arguments": json.dumps(dict(call.arguments), separators=(",", ":")),
                    }
                    for call in message.tool_calls
                )
            else:
                history.extend(
                    OpenAIResponsesClient._tool_result_to_api(result)
                    for result in message.tool_results
                )
        return history

    @staticmethod
    def _tool_to_api(tool: ToolSpec) -> dict[str, object]:
        return {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": dict(tool.input_schema),
            "strict": True,
        }

    @staticmethod
    def _tool_result_to_api(result: ToolResult) -> dict[str, object]:
        content = f"ERROR: {result.content}" if result.is_error else result.content
        return {
            "type": "function_call_output",
            "call_id": result.call_id,
            "output": content,
        }

    def _post(self, body: Mapping[str, object]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        connection = http.client.HTTPSConnection(_API_HOST, timeout=self._timeout_seconds)
        try:
            connection.request(
                "POST",
                _API_PATH,
                body=payload,
                headers={
                    "authorization": f"Bearer {self._api_key}",
                    "content-type": "application/json",
                },
            )
            response = connection.getresponse()
            raw = response.read()
        except (OSError, http.client.HTTPException) as exc:
            raise ModelProviderError("OpenAI Responses API request failed") from exc
        finally:
            connection.close()

        if response.status == 429:
            raise ModelRateLimitError(
                "OpenAI Responses API returned HTTP 429",
                retry_after=response.getheader("retry-after"),
            )
        if response.status < 200 or response.status >= 300:
            detail = safe_provider_error_detail(raw, secret=self._api_key)
            suffix = f": {detail}" if detail else ""
            raise ModelProviderError(
                f"OpenAI Responses API returned HTTP {response.status}{suffix}"
            )
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelProviderError("OpenAI Responses API returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError("OpenAI Responses API response must be a JSON object")
        return decoded

    @staticmethod
    def _extract_text(response: Mapping[str, Any]) -> str:
        output = response.get("output")
        if not isinstance(output, list):
            return ""
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "output_text":
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _extract_tool_calls(response: Mapping[str, Any]) -> tuple[ToolCall, ...]:
        output = response.get("output")
        if not isinstance(output, list):
            raise ModelProviderError("OpenAI Responses API response is missing output")
        calls: list[ToolCall] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            call_id = item.get("call_id")
            name = item.get("name")
            arguments_json = item.get("arguments")
            if not isinstance(call_id, str) or not isinstance(name, str):
                raise ModelProviderError("OpenAI Responses API returned malformed function call")
            if not isinstance(arguments_json, str):
                raise ModelProviderError("OpenAI Responses API returned malformed function arguments")
            try:
                arguments = json.loads(arguments_json)
            except json.JSONDecodeError as exc:
                raise ModelProviderError(
                    "OpenAI Responses API returned invalid tool arguments JSON"
                ) from exc
            if not isinstance(arguments, dict):
                raise ModelProviderError(
                    "OpenAI Responses API tool arguments must be a JSON object"
                )
            calls.append(ToolCall(call_id=call_id, name=name, arguments=arguments))
        return tuple(calls)

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

    @staticmethod
    def _stop_reason(response: Mapping[str, Any]) -> str:
        status = response.get("status")
        if status == "incomplete":
            details = response.get("incomplete_details")
            if isinstance(details, dict):
                reason = details.get("reason")
                if isinstance(reason, str) and reason:
                    return reason
        return str(status or "unknown")
