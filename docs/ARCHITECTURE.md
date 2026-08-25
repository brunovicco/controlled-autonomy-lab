# Architecture

## Purpose

Controlled Autonomy Lab makes one architecture decision visible: **who owns the next step?** Every implementation analyzes the same incident and evidence; only the control structure changes.

## Layering

```text
entrypoints -> application -> domain
entrypoints -> adapters
adapters    -> application/domain
domain      -> no outer layer
```

### Domain

Provider-neutral types only: incident/evidence, execution metadata, evaluator verdicts, tool specifications, tool calls and agent messages.

### Application

Owns control-flow policy: fixed workflow topology, route allowlists, evaluator retry budget, agent step/tool-call budgets, cross-incident authorization and repeated-run comparison.

`TextModel` and `AgentModel` are provider-neutral ports. `ModelClient` combines both capabilities only at composition time; individual patterns continue to depend on the narrowest interface they need.

### Adapters

Infrastructure translation is explicit:

```text
                         +-> Anthropic Messages API
application model ports-|
                         +-> OpenAI-compatible Chat Completions
                              + OpenAI preset
                              + Groq preset
                              + OpenRouter preset
                              + custom HTTPS endpoint
```

Both transports use the Python standard library. No provider SDK, LangChain or LangGraph dependency is required to understand the message/tool boundary.

`providers.py` is composition only: it selects an adapter from environment variables. Provider selection never changes agent permissions or workflow topology.

### Entrypoint

The CLI validates user-facing options, composes the selected provider and renders results. It does not own investigation rules.

## Pattern control flows

### Augmented LLM

```text
incident -> bounded evidence -> one model call -> answer
```

### Chaining

```text
incident -> extract facts -> assess -> recommend
```

### Routing

```text
                         -> deployment path
incident -> classifier  -> performance path
                         -> dependency path
                         -> security path
```

The model chooses a label; code converts it to a bounded enum and fails closed on anything else.

### Parallelization

```text
             -> metrics ----\
incident ----> changes ------> aggregate
             -> dependencies /
```

Application code owns fan-out/fan-in.

### Evaluator-optimizer

```text
             +---------------- feedback ----------------+
             |                                          |
incident -> generate -> evaluate -> pass? -> final     |
                         |                              |
                         +---- no -> revise ------------+
```

Evaluator output has an application-owned JSON contract and the revision budget is finite.

### Agent

```text
incident -> selected LLM
              |
              +-> metrics --------+
              |                    |
              +-> deployment -----+--> selected LLM -> ... -> final answer
              |                    |
              +-> runbook --------+
```

The sequence is model-controlled, but authority is not. Deterministic guards allow only five read-only tools, the active incident, at most six model turns and eight tool calls, with no production mutation tools.

## Trust boundaries

### External LLM provider

Live runs send the incident fixture and, for the agent, prior tool results to the selected provider. Credentials are read from provider-specific environment variables and are never written to metadata traces.

The provider boundary is untrusted input in both directions. Adapters validate HTTP status, JSON shape and tool-call structure before returning provider-neutral domain objects. Raw error bodies are not surfaced in exceptions.

### Custom base URL

The custom OpenAI-compatible adapter accepts only HTTPS URLs without embedded credentials, query strings or fragments. This reduces accidental secret exposure and prevents silently accepting a non-TLS provider endpoint.

### Tool boundary

A model tool request is untrusted. Application code verifies the exact tool allowlist, active `incident_id` and global call budget before evidence is returned.

### Observability boundary

`MetadataRunRecorder` stores only operational comparison metadata. It excludes prompts, answers, evidence bodies, tool arguments/results and credentials.

## Provider variance

`openrouter/free` intentionally optimizes accessibility rather than reproducibility because the underlying free model can vary. For controlled experiments, pin a concrete model/provider while holding the incident and autonomy budgets constant.

Provider token counters are retained as reported; the project does not pretend token accounting or pricing is identical across providers.

## Why no A2A or MCP in this version

There is no remote agent or MCP server boundary. Protocol infrastructure would obscure the architecture comparison. If a later phase moves an evaluator, evidence provider or specialist agent to another process, `a2a-otel-kit` becomes appropriate for W3C trace-context propagation and metadata-only OTLP spans across those real boundaries.

## Core invariant

> Escalate autonomy only when measurement shows the simpler pattern is insufficient.

The repository measures latency, token usage, model/tool-call count, quality behavior and trajectory variance so that statement can be tested rather than treated as a slogan.
