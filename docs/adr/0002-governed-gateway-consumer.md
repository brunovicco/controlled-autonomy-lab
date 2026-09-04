# ADR 0002 — Governed gateway as an incremental consumer boundary

Status: Accepted

## Context

Phase 14 of the Governed LLM Gateway roadmap migrates real consumers incrementally. The first recommended consumer is `controlled-autonomy-lab`.

The lab currently owns direct OpenAI Responses, Anthropic Messages, and OpenAI-compatible provider adapters. The gateway now owns provider credentials, policy authorization, deterministic routing, resilience, normalized tool calls, streaming, telemetry, benchmark-derived ranking, and optional Verifiable AI Governance enforcement.

The lab must remain a consumer. It must not become a gateway dependency and it must not recreate provider routing or authorization locally.

## Decision

Add an opt-in `gateway` provider mode for bounded text-generation runs.

The integration uses the thin `governed-llm-gateway-client` SDK and the provider-neutral gateway contracts. The consumer supplies only gateway URL/credential plus workload context. It does not receive provider credentials and does not choose a concrete provider/model/deployment.

The first migration slice deliberately covers `TextModel.complete` only. The existing bounded-agent loop requires provider-neutral tool-result continuation after a model-requested tool call. Gateway Phase 12 explicitly rejects tool-result continuation because provider-native continuation state is not yet part of the client contract. Encoding tool results as user text would change benchmark semantics and is therefore rejected.

Consequently:

- non-agent `run` patterns may use `LLM_PROVIDER=gateway`;
- the `agent` pattern fails closed in gateway mode with an explicit provider error;
- reproducible benchmark commands that include the agent pattern remain on the existing direct-provider adapters until the gateway exposes a real continuation contract;
- no automatic fallback from gateway mode to direct provider credentials is allowed.

## Authority and provenance

The gateway remains the sole operational model selector for gateway-mode calls. The lab declares workload/risk/data-classification context, but those values are not trusted authorization facts. Effective authorization remains server-side.

The consumer does not interpret routing provenance as authority and does not retry gateway requests. Provider retry/fallback stays server-side.

## Dependency pinning

Until the gateway client/contracts are published as independently versioned packages, the lab pins both packages to an exact Governed LLM Gateway commit. This avoids silently tracking gateway `main` and makes the integration case reproducible.

## Consequences

This is intentionally an incremental migration rather than a big-bang replacement of all provider adapters. Direct adapters remain available for benchmark comparability and for the bounded-agent continuation contract that the gateway does not yet support.
