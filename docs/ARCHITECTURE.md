# Architecture

## Purpose

Controlled Autonomy Lab makes one architecture decision visible: **who owns the next step?** Every pattern analyzes the same bounded incident/evidence fixture; the control structure changes while the authority boundary stays explicit.

The project now separates two concerns that are often collapsed in LLM demos:

1. **execution architecture** — who chooses the next step and tools;
2. **post-run evaluation architecture** — how factual support and claim semantics are checked without silently rewriting execution metrics.

## Layering

```text
entrypoints -> application -> domain
entrypoints -> adapters
adapters    -> application/domain
domain      -> no outer layer
```

### Domain

Provider-neutral types only: incident/evidence, execution metadata, evaluator verdicts, tool specifications, tool calls, agent messages, benchmark records, grounding reports, deterministic claim reports, and semantic merge/disagreement results.

### Application

Owns control-flow and evaluation policy:

- fixed workflow topology;
- route allowlists;
- evaluator revision budget;
- agent step/tool-call budgets;
- cross-incident authorization;
- repeated benchmark orchestration;
- deterministic Grounding v1;
- deterministic Claim Evaluation v2;
- selective semantic escalation and merge policy.

`TextModel` and `AgentModel` are provider-neutral ports. `ModelClient` combines both capabilities only at composition time; individual patterns depend on the narrowest interface they need.

### Adapters

Provider transport is explicit:

```text
                         +-> Anthropic Messages API
application model ports-+-> OpenAI Responses API
                         +-> OpenAI-compatible Chat Completions
                               +-> Groq
                               +-> OpenRouter
                               +-> custom HTTPS endpoint
```

All transports use the Python standard library. No provider SDK, LangChain, or LangGraph dependency is required to understand the message/tool boundary.

`providers.py` is composition only. Generator and semantic-judge provider selection comes from environment configuration; provider selection never changes agent permissions, workflow topology, Grounding v1 authority, or benchmark semantics.

### Entrypoints

Two entrypoint surfaces exist:

- `cli.py` — normal `run`, `compare`, `repeat`, and `benchmark` flows plus opt-in claim/semantic calibration on a single run;
- `semantic_judge_cli.py` — explicit generator × judge calibration with separately resolved provider/model identity.

The entrypoints validate user-facing options, compose providers, and render results. They do not own investigation or authority rules.

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

The model chooses a label; deterministic code converts it to a bounded enum and fails closed on anything else.

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
              +-> dependencies ---+
              |                    |
              +-> runbook --------+
              |                    |
              +-> prior incident -+
```

The sequence is model-controlled, but authority is not. Deterministic guards allow only five read-only tools, the active incident, at most six model turns and eight tool calls, with no production mutation tools.

## Evaluation stack

Post-run evaluation is intentionally layered.

```text
PatternRun
   |
   +-> Grounding Evaluation v1
   |      exact specifics
   |      associations
   |      causal overclaims
   |      proposal parameters
   |
   +-> Claim Evaluation v2
   |      SUPPORTED_FACT
   |      SUPPORTED_INFERENCE
   |      PROPOSED_ACTION
   |      UNSUPPORTED_CLAIM
   |
   +-> eligible conservative miss?
          |
          +-- no --> deterministic result remains final
          |
          +-- yes -> Semantic Claim Evaluation v2.1
                         |
                         +-> optional independent judge v2.2
                         +-> disagreement + resolution
```

### Grounding v1 authority

Grounding v1 is deterministic and fixture-backed. Unsupported versions, measurements, associations, or genuine causal overclaims are hard failures for claim evaluation.

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

A semantic model cannot explain away a deterministic hard failure.

### Deterministic Claim Evaluation v2

Claim Evaluation v2 classifies extracted statements as supported facts, supported inferences, proposed actions, or unsupported claims.

It remains conservative: exact and high-confidence bounded evidence is resolved locally; a paraphrase requiring real entailment can remain unsupported rather than being guessed.

### Selective semantic escalation v2.1

Only ordinary conservative `UNSUPPORTED_CLAIM` results are eligible. Deterministic support, proposed actions, and `grounding-v1-*` hard failures are skipped.

Semantic calls/tokens remain separate from the architecture pattern's original model-call/token accounting.

### Independent semantic judge v2.2

The semantic judge can be composed with a provider/model different from the generator.

```text
OpenAI generator
      ↓
PatternRun
      ↓
deterministic evaluation
      ↓
eligible claim
      ↓
Groq judge
      ↓
semantic verdict + disagreement
```

This removes implicit self-judging from calibration but does not make the second model ground truth. Judge identity is explicit and disagreement is retained as evidence.

## Trust boundaries

### External generator provider

Live runs send the bounded incident/evidence context to the selected provider. For the agent, later calls also include bounded prior tool results.

Credentials are read from provider-specific environment variables and are never written to metadata traces.

The provider boundary is untrusted input in both directions. Adapters validate HTTP status, JSON shape, text/tool-call structure, and safe provider errors before returning provider-neutral domain objects.

### External semantic judge

The judge receives only an eligible claim plus bounded evidence source ids/summaries. It is instructed not to use outside knowledge and must return a strict bounded JSON verdict.

The semantic layer validates:

- exact schema/field set;
- bounded verdict enum;
- rationale bounds;
- evidence source ids against the supplied source set;
- at least one source for supported verdicts.

Malformed or unbounded output is an evaluation failure, not permission to guess.

### Custom base URL

The custom OpenAI-compatible adapter accepts only HTTPS URLs without embedded credentials, query strings, or fragments. This reduces accidental secret exposure and prevents silently accepting a non-TLS provider endpoint.

### Tool boundary

A model tool request is untrusted. Application code verifies the exact tool allowlist, active `incident_id`, and global call budget before evidence is returned.

### Observability boundary

`MetadataRunRecorder` stores only operational comparison metadata. It excludes prompts, answers, evidence bodies, tool arguments/results, claim text, semantic judgement text, and credentials.

Claim-level and semantic analysis are immediate/opt-in calibration surfaces and are deliberately not written into the historical benchmark artifacts.

## Benchmark boundary

The repeated benchmark measures the six execution architectures. It does **not** currently include post-run semantic-judge metrics.

That separation is deliberate:

- benchmark model/tool calls describe pattern execution only;
- no hidden retries alter latency semantics;
- newer claim/semantic layers do not reclassify the historical 60-run dataset;
- semantic evaluator cost remains visible separately during calibration.

This keeps architecture-performance evidence and evaluator-development evidence from becoming one ambiguous score.

## Provider variance

`openrouter/free` intentionally optimizes accessibility rather than reproducibility because the underlying free model can vary. Controlled experiments pin a concrete provider/model while holding the incident and autonomy budgets constant.

Provider token counters are retained as reported; the project does not pretend token accounting or pricing is identical across providers.

## Why no A2A or MCP yet

There is still no real remote agent/MCP/distributed-process boundary. The independent semantic judge uses a separately configured provider, but it is still composed inside the same local process.

Protocol infrastructure would currently add ceremony without creating a real service boundary.

If a later phase moves the semantic judge, evidence provider, or specialist agent to another process/service, `a2a-otel-kit` becomes appropriate for W3C trace-context propagation and metadata-only OTLP spans across that real boundary.

## Core invariant

> Escalate autonomy only when measurement shows the simpler pattern is insufficient.

The repository measures latency, token usage, model/tool-call count, deterministic grounding, claim behavior, semantic disagreement, and trajectory variance so that statement can be tested rather than treated as a slogan.
