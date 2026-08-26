import http.client
import json
from typing import Any

import pytest

import autonomy_lab.adapters.anthropic as anthropic
from autonomy_lab.domain.agent import AgentMessage, ToolCall, ToolResult, ToolSpec
from autonomy_lab.domain.autonomy import ModelUsage


class FakeHTTPResponse:
    def __init__(
        self,
        payload: object,
        *,
        status: int = 200,
        raw: bytes | None = None,
    ) -> None:
        self.status = status
        self._raw = raw if raw is not None else json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw


class RecordingConnection:
    def __init__(self, response: FakeHTTPResponse) -> None:
        self._response = response
        self.request_body: bytes | None = None
        self.request_headers: dict[str, str] | None = None
        self.closed = False

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes,
        headers: dict[str, str],
    ) -> None:
        assert method == "POST"
        assert path == "/v1/messages"
        self.request_body = body
        self.request_headers = headers

    def getresponse(self) -> FakeHTTPResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


def _install_connection(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeHTTPResponse,
) -> RecordingConnection:
    connection = RecordingConnection(response)

    def factory(host: str, *, timeout: float) -> RecordingConnection:
        assert host == "api.anthropic.com"
        assert timeout == 30.0
        return connection

    monkeypatch.setattr(http.client, "HTTPSConnection", factory)
    return connection


def test_complete_maps_messages_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {
                "content": [{"type": "text", "text": "grounded answer"}],
                "usage": {"input_tokens": 21, "output_tokens": 7},
                "stop_reason": "end_turn",
            }
        ),
    )
    client = anthropic.AnthropicMessagesClient(api_key="test-key")

    turn = client.complete(system="system", prompt="prompt")

    assert turn.text == "grounded answer"
    assert turn.usage == ModelUsage(21, 7)
    assert turn.stop_reason == "end_turn"
    assert connection.closed is True
    assert connection.request_body is not None
    request = json.loads(connection.request_body)
    assert request["model"] == "claude-sonnet-5"
    assert request["messages"] == [{"role": "user", "content": "prompt"}]
    assert connection.request_headers is not None
    assert connection.request_headers["x-api-key"] == "test-key"


def test_next_turn_round_trips_provider_neutral_tool_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {
                "content": [
                    {"type": "text", "text": "I will inspect metrics."},
                    {
                        "type": "tool_use",
                        "id": "tool-2",
                        "name": "get_dependencies",
                        "input": {"incident_id": "INC-001"},
                    },
                ],
                "usage": {"input_tokens": 31, "output_tokens": 9},
                "stop_reason": "tool_use",
            }
        ),
    )
    client = anthropic.AnthropicMessagesClient(api_key="test-key")
    messages = (
        AgentMessage(role="user", text="Investigate INC-001"),
        AgentMessage(
            role="assistant",
            text="Checking metrics.",
            tool_calls=(
                ToolCall(
                    call_id="tool-1",
                    name="get_service_metrics",
                    arguments={"incident_id": "INC-001"},
                ),
            ),
        ),
        AgentMessage(
            role="tool",
            tool_results=(ToolResult(call_id="tool-1", content="5xx=8.7%"),),
        ),
    )
    tools = (
        ToolSpec(
            name="get_dependencies",
            description="Read dependency evidence.",
            input_schema={"type": "object", "properties": {}},
        ),
    )

    turn = client.next_turn(system="bounded", messages=messages, tools=tools)

    assert turn.message.text == "I will inspect metrics."
    assert turn.message.tool_calls[0].name == "get_dependencies"
    assert turn.usage == ModelUsage(31, 9)
    assert connection.request_body is not None
    request: dict[str, Any] = json.loads(connection.request_body)
    assert request["tool_choice"] == {"type": "auto"}
    assert request["tools"][0]["strict"] is True
    assert request["messages"][1]["content"][1]["type"] == "tool_use"
    assert request["messages"][2]["content"][0]["type"] == "tool_result"


def test_provider_http_error_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connection(
        monkeypatch,
        FakeHTTPResponse({"secret": "do-not-leak"}, status=429),
    )
    client = anthropic.AnthropicMessagesClient(api_key="test-key")

    with pytest.raises(anthropic.ModelProviderError, match="HTTP 429") as exc_info:
        client.complete(system="system", prompt="prompt")

    assert "do-not-leak" not in str(exc_info.value)


def test_provider_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connection(monkeypatch, FakeHTTPResponse({}, raw=b"not-json"))
    client = anthropic.AnthropicMessagesClient(api_key="test-key")

    with pytest.raises(anthropic.ModelProviderError, match="invalid JSON"):
        client.complete(system="system", prompt="prompt")


def test_client_configuration_fails_closed() -> None:
    with pytest.raises(ValueError, match="api_key"):
        anthropic.AnthropicMessagesClient(api_key="")
    with pytest.raises(ValueError, match="max_tokens"):
        anthropic.AnthropicMessagesClient(api_key="key", max_tokens=0)
    with pytest.raises(ValueError, match="timeout_seconds"):
        anthropic.AnthropicMessagesClient(api_key="key", timeout_seconds=0)
