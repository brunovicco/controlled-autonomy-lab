"""Incremental Governed LLM Gateway adapter for bounded text-generation runs."""

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass

from governed_llm_gateway_client import GatewayClient, GatewayClientError, GatewayHTTPError
from governed_llm_gateway_contracts import (
    DataClassification,
    Message,
    MessageRole,
    RiskLevel,
    StreamEventType,
)

from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.domain.agent import AgentMessage, AgentTurn, ToolSpec
from autonomy_lab.domain.autonomy import ModelTurn, ModelUsage


@dataclass(frozen=True, slots=True)
class GatewaySelection:
    """Non-secret gateway request identity used for reproducible run metadata."""

    workload: str
    risk_level: RiskLevel
    data_classification: DataClassification
    max_tokens: int
    timeout_seconds: float


class GovernedGatewayClient:
    """Synchronous lab adapter over the thin async gateway SDK.

    A fresh SDK client is created for each bounded lab call so its httpx connection pool
    never crosses event-loop boundaries. Retry and provider fallback remain server-side.
    """

    def __init__(self, selection: GatewaySelection) -> None:
        """Store only provider-neutral request context; gateway credentials remain SDK-owned."""
        self._selection = selection

    def complete(self, *, system: str, prompt: str) -> ModelTurn:
        """Execute one bounded text turn through the governed gateway."""
        return asyncio.run(self._complete(system=system, prompt=prompt))

    async def _complete(self, *, system: str, prompt: str) -> ModelTurn:
        text_parts: list[str] = []
        usage = ModelUsage()
        finish_reason = "end_turn"
        try:
            async with GatewayClient.from_env() as client:
                async for event in client.stream(
                    workload=self._selection.workload,
                    messages=(
                        Message(role=MessageRole.SYSTEM, content=system),
                        Message(role=MessageRole.USER, content=prompt),
                    ),
                    risk_level=self._selection.risk_level,
                    data_classification=self._selection.data_classification,
                    max_output_tokens=self._selection.max_tokens,
                    provider_timeout_seconds=self._selection.timeout_seconds,
                ):
                    if (
                        event.event_type is StreamEventType.CONTENT_DELTA
                        and event.delta is not None
                    ):
                        text_parts.append(event.delta)
                    elif (
                        event.event_type is StreamEventType.USAGE_COMPLETED
                        and event.usage is not None
                    ):
                        usage = ModelUsage(
                            input_tokens=event.usage.input_tokens,
                            output_tokens=event.usage.output_tokens,
                        )
                    elif event.event_type is StreamEventType.RESPONSE_COMPLETED:
                        finish_reason = event.finish_reason or finish_reason
                    elif event.event_type is StreamEventType.RESPONSE_FAILED:
                        code = "gateway_execution_failed"
                        if event.error is not None:
                            code = event.error.code
                        raise ModelProviderError(f"governed gateway execution failed: {code}")
        except GatewayHTTPError as exc:
            if exc.status_code == 429:
                raise ModelRateLimitError("governed gateway rate limited the request") from None
            raise ModelProviderError(
                f"governed gateway rejected the request: status={exc.status_code} code={exc.code}"
            ) from None
        except GatewayClientError as exc:
            raise ModelProviderError(
                f"governed gateway client failure: {type(exc).__name__}"
            ) from None

        text = "".join(text_parts)
        if not text:
            raise ModelProviderError("governed gateway returned no text content")
        return ModelTurn(text=text, usage=usage, stop_reason=finish_reason)

    def next_turn(
        self,
        *,
        system: str,
        messages: tuple[AgentMessage, ...],
        tools: tuple[ToolSpec, ...],
    ) -> AgentTurn:
        """Fail closed until the gateway SDK defines provider-neutral tool-result continuation."""
        del system, messages, tools
        raise ModelProviderError(
            "governed gateway mode does not yet support bounded-agent tool-result continuation"
        )


def gateway_client_from_env(
    env: Mapping[str, str] | None = None,
    *,
    namespace: str = "",
) -> tuple[GovernedGatewayClient, GatewaySelection]:
    """Build the gateway adapter from explicit provider-neutral workload settings."""
    settings = os.environ if env is None else env
    workload = _required(settings, "GATEWAY_WORKLOAD", namespace=namespace)
    risk_level = _enum_setting(
        settings,
        "GATEWAY_RISK_LEVEL",
        RiskLevel,
        RiskLevel.LOW,
        namespace=namespace,
    )
    data_classification = _enum_setting(
        settings,
        "GATEWAY_DATA_CLASSIFICATION",
        DataClassification,
        DataClassification.PUBLIC,
        namespace=namespace,
    )
    max_tokens = _positive_int(settings, "LLM_MAX_TOKENS", 1200, namespace=namespace)
    timeout_seconds = _positive_float(
        settings,
        "LLM_TIMEOUT_SECONDS",
        30.0,
        namespace=namespace,
    )
    selection = GatewaySelection(
        workload=workload,
        risk_level=risk_level,
        data_classification=data_classification,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )
    return GovernedGatewayClient(selection), selection


def _value(settings: Mapping[str, str], name: str, *, namespace: str) -> str | None:
    if namespace:
        namespaced = settings.get(f"{namespace}{name}")
        if namespaced is not None:
            return namespaced
    return settings.get(name)


def _required(settings: Mapping[str, str], name: str, *, namespace: str) -> str:
    value = _value(settings, name, namespace=namespace)
    display = f"{namespace}{name}" if namespace else name
    if value is None or not value.strip() or value.strip() != value:
        raise SystemExit(f"{display} is required and must be normalized when LLM_PROVIDER=gateway")
    return value


def _enum_setting[T: (RiskLevel, DataClassification)](
    settings: Mapping[str, str],
    name: str,
    enum_type: type[T],
    default: T,
    *,
    namespace: str,
) -> T:
    raw = _value(settings, name, namespace=namespace)
    if raw is None:
        return default
    try:
        return enum_type(raw)
    except ValueError as exc:
        display = f"{namespace}{name}" if namespace else name
        allowed = ", ".join(item.value for item in enum_type)
        raise SystemExit(f"{display} must be one of: {allowed}") from exc


def _positive_int(
    settings: Mapping[str, str],
    name: str,
    default: int,
    *,
    namespace: str,
) -> int:
    raw = _value(settings, name, namespace=namespace)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be a positive integer")
    return value


def _positive_float(
    settings: Mapping[str, str],
    name: str,
    default: float,
    *,
    namespace: str,
) -> float:
    raw = _value(settings, name, namespace=namespace)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be positive") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be positive")
    return value
