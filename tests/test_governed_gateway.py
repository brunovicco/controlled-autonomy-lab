from types import SimpleNamespace

import pytest
from governed_llm_gateway_client import GatewayClient
from governed_llm_gateway_contracts import DataClassification, RiskLevel, StreamEventType

from autonomy_lab.adapters.governed_gateway import gateway_client_from_env
from autonomy_lab.adapters.providers import configured_client_from_env
from autonomy_lab.application.model_errors import ModelProviderError
from autonomy_lab.domain.agent import AgentMessage


def test_gateway_provider_requires_explicit_workload() -> None:
    with pytest.raises(SystemExit, match="GATEWAY_WORKLOAD is required"):
        configured_client_from_env({"LLM_PROVIDER": "gateway"})


def test_gateway_provider_exposes_policy_routed_identity_without_provider_key() -> None:
    client, selection = configured_client_from_env(
        {
            "LLM_PROVIDER": "gateway",
            "GATEWAY_WORKLOAD": "incident.analysis",
            "GATEWAY_RISK_LEVEL": "medium",
            "GATEWAY_DATA_CLASSIFICATION": "internal",
            "LLM_MAX_TOKENS": "900",
            "LLM_TIMEOUT_SECONDS": "12.5",
        }
    )

    assert selection.provider == "gateway"
    assert selection.model == "policy-routed:incident.analysis"
    assert selection.max_tokens == 900
    assert selection.timeout_seconds == 12.5
    assert client._selection.risk_level is RiskLevel.MEDIUM
    assert client._selection.data_classification is DataClassification.INTERNAL


def test_gateway_provider_rejects_unknown_controlled_vocabulary() -> None:
    with pytest.raises(SystemExit, match="GATEWAY_RISK_LEVEL must be one of"):
        gateway_client_from_env(
            {
                "GATEWAY_WORKLOAD": "incident.analysis",
                "GATEWAY_RISK_LEVEL": "unbounded",
            }
        )


def test_gateway_agent_continuation_fails_closed() -> None:
    client, _ = gateway_client_from_env({"GATEWAY_WORKLOAD": "incident.analysis"})

    with pytest.raises(ModelProviderError, match="tool-result continuation"):
        client.next_turn(
            system="bounded",
            messages=(AgentMessage(role="user", text="inspect"),),
            tools=(),
        )


def test_gateway_complete_maps_text_usage_and_finish_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, object] = {}

    class FakeGateway:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def stream(self, **kwargs):
            observed.update(kwargs)
            yield SimpleNamespace(
                event_type=StreamEventType.CONTENT_DELTA,
                delta="bounded ",
                usage=None,
                finish_reason=None,
                error=None,
            )
            yield SimpleNamespace(
                event_type=StreamEventType.CONTENT_DELTA,
                delta="answer",
                usage=None,
                finish_reason=None,
                error=None,
            )
            yield SimpleNamespace(
                event_type=StreamEventType.USAGE_COMPLETED,
                delta=None,
                usage=SimpleNamespace(input_tokens=21, output_tokens=8),
                finish_reason=None,
                error=None,
            )
            yield SimpleNamespace(
                event_type=StreamEventType.RESPONSE_COMPLETED,
                delta=None,
                usage=None,
                finish_reason="stop",
                error=None,
            )

    monkeypatch.setattr(GatewayClient, "from_env", classmethod(lambda cls: FakeGateway()))
    client, _ = gateway_client_from_env(
        {
            "GATEWAY_WORKLOAD": "incident.analysis",
            "GATEWAY_RISK_LEVEL": "low",
            "GATEWAY_DATA_CLASSIFICATION": "public",
            "LLM_MAX_TOKENS": "500",
            "LLM_TIMEOUT_SECONDS": "9",
        }
    )

    turn = client.complete(system="system", prompt="prompt")

    assert turn.text == "bounded answer"
    assert turn.usage.input_tokens == 21
    assert turn.usage.output_tokens == 8
    assert turn.stop_reason == "stop"
    assert observed["workload"] == "incident.analysis"
    assert observed["risk_level"] is RiskLevel.LOW
    assert observed["data_classification"] is DataClassification.PUBLIC
    assert observed["max_output_tokens"] == 500
    assert observed["provider_timeout_seconds"] == 9.0
    assert len(observed["messages"]) == 2


def test_gateway_complete_rejects_empty_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyGateway:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def stream(self, **kwargs):
            del kwargs
            yield SimpleNamespace(
                event_type=StreamEventType.RESPONSE_COMPLETED,
                delta=None,
                usage=None,
                finish_reason="stop",
                error=None,
            )

    monkeypatch.setattr(GatewayClient, "from_env", classmethod(lambda cls: EmptyGateway()))
    client, _ = gateway_client_from_env({"GATEWAY_WORKLOAD": "incident.analysis"})

    with pytest.raises(ModelProviderError, match="no text content"):
        client.complete(system="system", prompt="prompt")
