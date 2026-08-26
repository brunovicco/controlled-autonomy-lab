import http.client
import json
from typing import Any

import pytest

import autonomy_lab.adapters.openai_compatible as compatible
from autonomy_lab.application.model_errors import ModelRateLimitError
from autonomy_lab.domain.agent import AgentMessage, ToolCall, ToolResult, ToolSpec
from autonomy_lab.domain.autonomy import ModelUsage


class FakeHTTPResponse:
    def __init__(
        self,
        payload: object,
        *,
        status: int = 200,
        raw: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._raw = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self._headers = {key.lower(): value for key, value in (headers or {}).items()}

    def read(self) -> bytes:
        return self._raw

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)


class RecordingConnection:
    def __init__(self, response: FakeHTTPResponse) -> None:
        self._response = response
        self.request_path = ""
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
        self.request_path = path
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

    def factory(
        host: str,
        port: int | None = None,
        *,
        timeout: float,
    ) -> RecordingConnection:
        assert host == "api.groq.com"
        assert port is None
        assert timeout == 30.0
        return connection

    monkeypatch.setattr(http.client, "HTTPSConnection", factory)
    return connection


def _client() -> compatible.OpenAICompatibleChatClient:
    return compatible.OpenAICompatibleChatClient(
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        model="openai/gpt-oss-20b",
        provider_label="Groq API",
    )


def test_complete_maps_chat_completion_response(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "grounded answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 21, "completion_tokens": 7},
            }
        ),
    )

    turn = _client().complete(system="system", prompt="prompt")

    assert turn.text == "grounded answer"
    assert turn.usage == ModelUsage(21, 7)
    assert turn.stop_reason == "stop"
    assert connection.closed is True
    assert connection.request_path == "/openai/v1/chat/completions"
    assert connection.request_body is not None
    request = json.loads(connection.request_body)
    assert request["model"] == "openai/gpt-oss-20b"
    assert request["max_completion_tokens"] == 1200
    assert request["messages"][0] == {"role": "system", "content": "system"}
    assert connection.request_headers is not None
    assert connection.request_headers["authorization"] == "Bearer test-key"


def test_next_turn_round_trips_function_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "I will inspect dependencies.",
                            "tool_calls": [
                                {
                                    "id": "call-2",
                                    "type": "function",
                                    "function": {
                                        "name": "get_dependencies",
                                        "arguments": '{"incident_id":"INC-001"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 31, "completion_tokens": 9},
            }
        ),
    )
    messages = (
        AgentMessage(role="user", text="Investigate INC-001"),
        AgentMessage(
            role="assistant",
            text="Checking metrics.",
            tool_calls=(
                ToolCall(
                    call_id="call-1",
                    name="get_service_metrics",
                    arguments={"incident_id": "INC-001"},
                ),
            ),
        ),
        AgentMessage(
            role="tool",
            tool_results=(ToolResult(call_id="call-1", content="5xx=8.7%"),),
        ),
    )
    tools = (
        ToolSpec(
            name="get_dependencies",
            description="Read dependency evidence.",
            input_schema={"type": "object", "properties": {}},
        ),
    )

    turn = _client().next_turn(system="bounded", messages=messages, tools=tools)

    assert turn.message.text == "I will inspect dependencies."
    assert turn.message.tool_calls[0].name == "get_dependencies"
    assert turn.usage == ModelUsage(31, 9)
    assert connection.request_body is not None
    request: dict[str, Any] = json.loads(connection.request_body)
    assert request["tool_choice"] == "auto"
    assert request["tools"][0]["function"]["parameters"] == {
        "type": "object",
        "properties": {},
    }
    assert request["messages"][2]["tool_calls"][0]["type"] == "function"
    assert request["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "5xx=8.7%",
    }


def test_rate_limit_error_is_typed_redacted_and_preserves_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {"secret": "do-not-leak"},
            status=429,
            headers={"retry-after": "7"},
        ),
    )

    with pytest.raises(ModelRateLimitError, match="HTTP 429") as exc_info:
        _client().complete(system="system", prompt="prompt")

    assert "do-not-leak" not in str(exc_info.value)
    assert exc_info.value.retry_after == "7"


def test_provider_rejects_invalid_tool_argument_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connection(
        monkeypatch,
        FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {"name": "get_dependencies", "arguments": "{"},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }
        ),
    )

    with pytest.raises(compatible.ModelProviderError, match="arguments JSON"):
        _client().next_turn(system="system", messages=(), tools=())


def test_client_configuration_fails_closed() -> None:
    with pytest.raises(ValueError, match="api_key"):
        compatible.OpenAICompatibleChatClient(
            api_key="",
            base_url="https://x.test/v1",
            model="m",
        )
    with pytest.raises(ValueError, match="plain HTTPS"):
        compatible.OpenAICompatibleChatClient(
            api_key="key",
            base_url="http://x.test/v1",
            model="m",
        )
    with pytest.raises(ValueError, match="model"):
        compatible.OpenAICompatibleChatClient(
            api_key="key",
            base_url="https://x.test/v1",
            model="",
        )
