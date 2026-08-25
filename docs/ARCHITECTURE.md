# Architecture

## Purpose

Controlled Autonomy Lab makes one architecture decision visible: **who owns the next step?**

Every implementation analyzes the same incident and evidence. Only the control structure changes.

## Layering

```text
entrypoints -> application -> domain
entrypoints -> adapters
adapters    -> application/domain
domain      -> no outer layer
```

### Domain

Provider-neutral types only:

- incident and evidence;
- pattern execution metadata;
- evaluator verdicts;
- tool specifications, tool calls, and agent messages.

### Application

Owns all control-flow policies:

- fixed workflow topology;
- route allowlists;
- evaluator retry budget;
- agent step and tool-call budgets;
- cross-incident authorization checks;
- repeated-run comparison.

### Adapters

Own infrastructure details:

- deterministic in-memory evidence fixture;
- Anthropic Messages API serialization/deserialization;
- metadata-only JSONL run recording.

The Anthropic adapter intentionally uses the standard library rather than introducing a framework. This keeps the architectural primitive visible: a message call, optional client tools, and tool results.

### Entrypoints

The CLI validates user-facing options, constructs dependencies, and renders results. It does not own investigation rules.

## Pattern control flows

### Augmented LLM

```text
incident
   |
load bounded evidence
   |
one model call
   |
answer
```

Application code owns the entire path.

### Chaining

```text
incident -> extract facts -> assess -> recommend
```

Each handoff is explicit. A model can judge within a step but cannot skip, add, or reorder steps.

### Routing

```text
                         -> deployment path
incident -> classifier  -> performance path
                         -> dependency path
                         -> security path
```

The model chooses a label. Code converts that label to `IncidentCategory`; anything outside the enum fails closed.

### Parallelization

```text
             -> metrics ----\
incident ----> changes ------> aggregate
             -> dependencies /
```

The three specialist calls are independent and execute concurrently. Application code still owns fan-out and fan-in.

### Evaluator-optimizer

```text
             +---------------- feedback ----------------+
             |                                          |
incident -> generate -> evaluate -> pass? -> final     |
                         |                              |
                         +---- no -> revise ------------+
```

Guards:

- evaluator output must match the application-owned JSON contract;
- the revision budget is finite;
- failure to meet quality after the budget raises an explicit error.

### Agent

```text
incident -> Claude
             |
             +-> metrics --------+
             |                    |
             +-> deployment -----+--> Claude -> ... -> final answer
             |                    |
             +-> runbook --------+
```

The exact sequence is not encoded in application code. The model chooses tools based on prior results.

That autonomy is bounded by deterministic guards:

```text
model autonomy
    |
    +-- only five read-only tools
    +-- active incident only
    +-- max 6 model turns
    +-- max 8 tool calls
    +-- no production mutation tools
```

## Trust boundaries

### Claude API

Outbound content can include incident fixture data and prior tool results. The API key is read only from `ANTHROPIC_API_KEY` and is never written to run traces.

The default model is configurable through `CLAUDE_MODEL`; keeping it out of control-flow code makes model upgrades independent from architecture changes.

### Tool boundary

A model tool request is untrusted input. The application checks:

1. tool name exists in the allowlist;
2. `incident_id` exactly matches the current incident;
3. the global tool-call budget has not been exceeded.

Only then does code return evidence.

### Observability boundary

`MetadataRunRecorder` stores operational metadata but deliberately excludes:

- prompts;
- answers;
- evidence content;
- tool arguments/results;
- secrets.

This lets repeated executions be compared without turning observability into a second data store for model content.

## Why no A2A or MCP in the first version

There is no remote agent or MCP server boundary in this implementation. Introducing protocols only to display them would obscure the architectural comparison.

When a later phase moves the evaluator or evidence provider to another process, `a2a-otel-kit` becomes appropriate for W3C trace-context propagation and metadata-only OTLP spans across those real boundaries.

## Core invariant

> Escalate autonomy only when measurement shows the simpler pattern is insufficient.

The repository is designed so that this statement can be tested with latency, token usage, tool-call count, quality behavior, and trajectory variance rather than accepted as an architectural slogan.
