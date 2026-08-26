import http.client
import json
from typing import Any

import pytest

import autonomy_lab.adapters.openai_responses as responses
from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.domain.agent import AgentMessage, ToolResult, ToolSpec
from autonomy_lab.domain.autonomy import ModelUsage


class FakeHTTPResponse:
    def __init__(
        self,
        payload: object,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")
        self._headers = {key.lower(): value for key, value in (headers or {}).items()}

    def read(self) -> bytes:
        return self._raw

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)


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
        assert path == "/v1/responses"
        self.request_body = body
        self.request_headers = headers

    def getresponse(self) -> FakeHTTPResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


def _install_connections(
    monkeypatch: pytest.MonkeyPatch,
    fake_responses: list[FakeHTTPResponse],
) -> list[RecordingConnection]:
    connections: list[RecordingConnection] = []

    def factory(host: str, *, timeout: float) -> RecordingConnection:
        assert host == "api.openai.com"
        assert timeout == 30.0
        connection = RecordingConnection(fake_responses[len(connections)])
        connections.append(connection)
        return connection

    monkeypatch.setattr(http.client, "HTTPSConnection", factory)
    return connections


def _client() -> responses.OpenAIResponsesClient:
    return responses.OpenAIResponsesClient(api_key="test-key", model="gpt-5.6-luna")


def test_complete_maps_responses_text_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = _install_connections(
        monkeypatch,
        [
            FakeHTTPResponse(
                {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "grounded answer"}],
                        }
                    ],
                    "usage": {"input_tokens": 21, "output_tokens": 7},
                }
            )
        ],
    )

    turn = _client().complete(system="system", prompt="prompt")

    assert turn.text == "grounded answer"
    assert turn.usage == ModelUsage(21, 7)
    assert turn.stop_reason == "completed"
    request = json.loads(connections[0].request_body or b"{}")
    assert request["model"] == "gpt-5.6-luna"
    assert request["store"] is False
    assert request["max_output_tokens"] == 1200
    assert request["instructions"] == "system"
    assert request["input"] == [{"role": "user", "content": "prompt"}]


def test_agent_replays_reasoning_and_function_output_statelessly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reasoning_item = {
        "type": "reasoning",
        "id": "rs_1",
        "summary": [],
        "encrypted_content": "opaque-reasoning",
    }
    function_call = {
        "type": "function_call",
        "id": "fc_1",
        "call_id": "call_1",
        "name": "get_service_metrics",
        "arguments": '{"incident_id":"INC-001"}',
    }
    connections = _install_connections(
        monkeypatch,
        [
            FakeHTTPResponse(
                {
                    "status": "completed",
                    "output": [reasoning_item, function_call],
                    "usage": {"input_tokens": 30, "output_tokens": 12},
                }
            ),
            FakeHTTPResponse(
                {
                    "status": "completed",
                    "output": [
                        {"type": "reasoning", "id": "rs_2", "summary": []},
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "final assessment"}],
                        },
                    ],
                    "usage": {"input_tokens": 44, "output_tokens": 18},
                }
            ),
        ],
    )
    client = _client()
    tools = (
        ToolSpec(
            name="get_service_metrics",
            description="Read metrics.",
            input_schema={
                "type": "object",
                "properties": {"incident_id": {"type": "string"}},
                "required": ["incident_id"],
                "additionalProperties": False,
            },
        ),
    )

    first = client.next_turn(
        system="bounded",
        messages=(AgentMessage(role="user", text="Investigate INC-001"),),
        tools=tools,
    )

    assert first.message.tool_calls[0].name == "get_service_metrics"
    first_request: dict[str, Any] = json.loads(connections[0].request_body or b"{}")
    assert first_request["store"] is False
    assert first_request["tools"][0]["strict"] is True
    assert first_request["tools"][0]["name"] == "get_service_metrics"

    second = client.next_turn(
        system="bounded",
        messages=(
            AgentMessage(role="user", text="Investigate INC-001"),
            first.message,
            AgentMessage(
                role="tool",
                tool_results=(ToolResult(call_id="call_1", content="5xx=8.7%"),),
            ),
        ),
        tools=tools,
    )

    assert second.message.text == "final assessment"
    assert second.message.tool_calls == ()
    second_request: dict[str, Any] = json.loads(connections[1].request_body or b"{}")
    history = second_request["input"]
    assert history[0] == {"role": "user", "content": "Investigate INC-001"}
    assert reasoning_item in history
    assert function_call in history
    assert history[-1] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "5xx=8.7%",
    }


def test_rate_limit_is_typed_and_preserves_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connections(
        monkeypatch,
        [
            FakeHTTPResponse(
                {"error": {"message": "slow down"}},
                status=429,
                headers={"retry-after": "3"},
            )
        ],
    )

    with pytest.raises(ModelRateLimitError, match="HTTP 429") as exc_info:
        _client().complete(system="system", prompt="prompt")

    assert exc_info.value.retry_after == "3"


def test_http_error_uses_safe_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connections(
        monkeypatch,
        [
            FakeHTTPResponse(
                {
                    "error": {
                        "type": "invalid_request_error",
                        "message": "bad request for sk-secret-value and Bearer abc123",
                    }
                },
                status=400,
            )
        ],
    )

    with pytest.raises(ModelProviderError, match="invalid_request_error") as exc_info:
        _client().complete(system="system", prompt="prompt")

    text = str(exc_info.value)
    assert "sk-secret-value" not in text
    assert "Bearer abc123" not in text


def test_incomplete_text_response_surfaces_stop_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_connections(
        monkeypatch,
        [
            FakeHTTPResponse(
                {
                    "status": "incomplete",
                    "incomplete_details": {"reason": "max_output_tokens"},
                    "output": [{"type": "reasoning", "id": "rs_1", "summary": []}],
                }
            )
        ],
    )

    with pytest.raises(ModelProviderError, match="stop_reason=max_output_tokens"):
        _client().complete(system="system", prompt="prompt")
