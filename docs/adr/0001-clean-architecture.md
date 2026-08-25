# ADR-0001: Keep autonomy patterns behind Clean Architecture boundaries

- Status: Accepted
- Date: 2026-08-25

## Context

The lab must compare orchestration patterns without coupling the experiment to an LLM provider, SDK or framework.

## Decision

Keep domain and application layers provider-neutral. External model protocols live in adapters, while the entrypoint selects a concrete adapter. Architecture validation remains part of the deterministic quality gate.

## Consequences

- The same six patterns can run against multiple providers.
- Provider serialization is explicit and independently tested.
- Agent authority remains application-owned even when the provider changes.
- Adding a provider may require mapping protocol differences at the adapter boundary.
