# Controlled Autonomy Lab

> Same incident. Different levels of LLM autonomy. Multiple providers.

Controlled Autonomy Lab is a small Python reference implementation for comparing six LLM application architectures against the same bounded production incident.

The central question is not whether agents are better than workflows. It is:

> **Who owns the next step: deterministic application code or the model?**

The lab makes that delegation boundary observable through execution topology, tool use, latency, token usage, deterministic grounding, claim-level evaluation, and selective semantic judgement.

## What this case demonstrates

The same incident can be solved with six different control patterns:

1. Augmented LLM
2. Prompt chaining
3. Routing
4. Parallelization
5. Evaluator-optimizer
6. Bounded tool-using agent

The project then evaluates the resulting behavior through progressively stronger—but deliberately separate—layers:

```text
pattern execution
      ↓
Grounding Evaluation v1
exact specifics, associations, causal discipline
      ↓
Claim Evaluation v2
fact vs inference vs action vs unsupported claim
      ↓
selective semantic escalation v2.1
only conservative deterministic misses
      ↓
independent semantic judge v2.2
optional generator × judge decoupling
```

The authority rule is intentionally asymmetric:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

An LLM judge may improve coverage for a conservative paraphrase miss, but it cannot explain away an unsupported version, measurement, association, or genuine causal overclaim.

## Evidence so far

### Repeated architecture benchmark

Two repeated live experiments used the same `INC-001` fixture and the same frozen benchmark commit, with five runs per pattern and no hidden retries.

Across OpenAI and Groq, **60/60 pattern executions completed successfully**.

| Pattern | OpenAI grounding | OpenAI p50 | Groq grounding | Groq p50 |
| --- | ---: | ---: | ---: | ---: |
| Augmented | 100.0% | 8.85s | 88.3% | 1.49s |
| Chaining | 90.0% | 28.32s | 67.4% | 4.26s |
| Routing | 100.0% | 8.61s | 87.8% | 2.12s |
| Parallel | 92.8% | 24.79s | 87.1% | 3.09s |
| Evaluator-optimizer | 100.0% | 9.38s | 88.5% | 2.11s |
| Agent | 100.0% | 10.38s | 82.6% | 4.00s |

These are **provider/model/configuration bundle** results, not a pure model leaderboard. OpenAI and Groq used different transports, token budgets, reasoning settings, pacing, infrastructure, and token accounting.

The strongest observations from the current dataset are:

- chaining had the lowest specific-grounding ratio in both provider experiments;
- evaluator-optimizer was consistently competitive on grounding;
- the bounded agent exposed provider/model-dependent trajectory behavior;
- OpenAI agent runs produced one trajectory across five runs, while Groq agent runs produced four;
- `100%` specific grounding did not imply full causal discipline—for example, OpenAI routing reached `100%` grounding while still producing causal overclaims.

See [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) for the full tables, methodology, threats to validity, and explicit non-claims.

### Claim-level calibration

Grounding v1 deliberately checks a narrow set of deterministic signals. Claim Evaluation v2 adds a second view:

| Claim kind | Meaning |
| --- | --- |
| `SUPPORTED_FACT` | bounded evidence supports a declarative claim |
| `SUPPORTED_INFERENCE` | a qualified inference is evidence-anchored |
| `PROPOSED_ACTION` | a recommendation or mitigation, not an observed fact |
| `UNSUPPORTED_CLAIM` | support is missing or a hard grounding failure exists |

A static observed-run fixture keeps this layer regression-testable without consuming provider quota.

See [`docs/CLAIM_EVALUATION.md`](docs/CLAIM_EVALUATION.md).

### Selective semantic escalation

The deterministic evaluator intentionally leaves some faithful paraphrases unsupported rather than pretending to perform NLI.

Semantic Claim Evaluation v2.1 therefore evaluates only eligible conservative misses. Live calibration reduced semantic work from three calls to one after two current-incident facts were moved back into deterministic high-confidence matching.

The remaining historical-context paraphrase required actual semantic entailment and was upgraded without weakening the Grounding v1 hard-failure rule.

See [`docs/SEMANTIC_CLAIM_EVALUATION.md`](docs/SEMANTIC_CLAIM_EVALUATION.md).

### Generator × judge decoupling

Semantic Judge Decoupling v2.2 separates answer generation from semantic judgement.

Two live bounded-agent smokes used:

```text
generator: OpenAI / gpt-5.6-luna
judge:     Groq / openai/gpt-oss-20b
self_judge: false
```

In both smokes:

- the agent used two generator model calls and five tools;
- only one conservative historical claim was escalated;
- the Groq judge upgraded that claim using `previous-incidents`;
- semantic usage remained separate from pattern execution metrics;
- `disagreement` remained explicit rather than silently collapsed.

The smokes also exposed two deterministic evaluator bugs that were fixed and frozen as regressions: explicit causal uncertainty (`does not prove ... caused`) and explicit causal rejection (`avoid treating ... as root cause`).

These smokes validate the **routing and authority architecture**, not judge accuracy or ground truth.

See [`docs/SEMANTIC_JUDGE_DECOUPLING.md`](docs/SEMANTIC_JUDGE_DECOUPLING.md).

## Common incident

Every architecture currently receives `INC-001`:

- service: `checkout-api`;
- HTTP 5xx rises from `0.2%` to `8.7%`;
- p95 latency rises from `310ms` to `2840ms`;
- `v2.18.4` was deployed at `13:58` with a new payment-provider timeout configuration;
- payment-provider latency also increased shortly after `14:00`;
- no provider outage is confirmed;
- a previous incident provides historical context but is not evidence of the current root cause.

The fixture intentionally creates correlation without proving causality. Good output must distinguish observed facts, hypotheses, historical context, and reversible recommendations.

## Control model

| Pattern | Who owns the path? | Model calls | Tool use | Main guard |
| --- | --- | ---: | ---: | --- |
| Augmented LLM | application | 1 | no | one bounded call |
| Chaining | application | 3 | no | fixed handoffs |
| Routing | application + classifier | 2 | no | route allowlist |
| Parallelization | application | 4 | no | fixed fan-out/fan-in |
| Evaluator-optimizer | application | variable | no | schema + revision budget |
| Agent | model | variable | yes | tool allowlist + step/tool budgets |

The distinction is architectural: when deterministic code owns the next step, execution topology is fixed by construction. When the model owns the next step, provider/model behavior may also change the trajectory itself.

## Architecture

```text
src/autonomy_lab/
├── domain/
│   ├── autonomy.py                    # provider-neutral run contracts
│   ├── benchmark.py                   # benchmark records and summaries
│   ├── grounding.py                   # deterministic grounding result types
│   ├── claim_evaluation.py            # claim taxonomy/result contracts
│   └── semantic_claim_evaluation.py   # semantic merge/disagreement contracts
├── application/
│   ├── model_ports.py                 # common text + tool-use model boundary
│   ├── model_errors.py                # provider-neutral error contract
│   ├── benchmark.py                   # repeated benchmark orchestration
│   ├── grounding.py                   # fixture-backed deterministic grounding
│   ├── claim_evaluation.py            # deterministic claim classification
│   ├── semantic_claim_evaluation.py   # selective semantic evaluation + merge
│   └── patterns/                      # six autonomy patterns
├── adapters/
│   ├── anthropic.py                   # native Anthropic Messages
│   ├── openai_responses.py            # native OpenAI Responses
│   ├── openai_compatible.py           # Groq/OpenRouter/custom Chat Completions
│   ├── providers.py                   # generator + semantic judge composition
│   ├── incidents.py                   # bounded incident/evidence fixture
│   ├── benchmark_artifacts.py
│   ├── benchmark_metadata.py
│   └── run_log.py
├── cli.py                             # run / compare / repeat / benchmark
└── semantic_judge_cli.py              # generator × judge calibration surface
```

The project started from [`claude-python-engineering-harness`](https://github.com/brunovicco/claude-python-engineering-harness), but generic scaffold not needed by this case was removed. The deterministic quality runner and architecture validator were retained because they still enforce project behavior.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Provider support

The runtime is provider-neutral and currently includes three transport adapters:

- native Anthropic Messages API;
- native OpenAI Responses API;
- OpenAI-compatible Chat Completions + function calling for Groq, OpenRouter and custom endpoints.

| Provider | `LLM_PROVIDER` | Default model | Cost path |
| --- | --- | --- | --- |
| Anthropic | `anthropic` | `claude-sonnet-5` | paid API |
| OpenAI | `openai` | `gpt-5.6-luna` | paid API |
| Groq | `groq` | `openai/gpt-oss-20b` | Free Plan available |
| OpenRouter | `openrouter` | `openrouter/free` | free router |
| Custom OpenAI-compatible | `custom` | user-defined | provider-dependent |

OpenAI uses `/v1/responses` for both text and tool-use calls. The adapter sets `store=false`; during a bounded agent run it keeps returned Responses output items only in memory so provider reasoning items can be replayed with subsequent function outputs. Provider-specific reasoning state does not enter the domain model or benchmark artifacts.

See [`docs/PROVIDERS.md`](docs/PROVIDERS.md).

## Quick start

Requirements: Python 3.13/3.14 and `uv`.

```bash
uv sync --frozen --all-groups
```

Free-provider example with OpenRouter:

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL=openrouter/free

uv run autonomy-lab run augmented --incident INC-001
```

Or Groq:

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY="..."
export GROQ_MODEL=openai/gpt-oss-20b

uv run autonomy-lab run agent --incident INC-001
```

`.env.example` is a reference file. The application intentionally does not auto-load `.env` files or add a dotenv dependency; export variables through your shell or preferred secret/configuration mechanism.

## Run and compare

One pattern:

```bash
uv run autonomy-lab run augmented --incident INC-001
```

Grounding:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding
```

Grounding + deterministic claims:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims \
  --json
```

Grounding + claims + same-model semantic calibration:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --semantic-claims \
  --json
```

All patterns:

```bash
uv run autonomy-lab compare --incident INC-001
```

Trajectory variance:

```bash
uv run autonomy-lab repeat agent --incident INC-001 --runs 5
```

Live runs can consume provider quota or paid tokens.

## Independent semantic judge calibration

Generator settings use the normal `LLM_*` namespace. The judge can use the independent `SEMANTIC_*` namespace.

Example: OpenAI generator + Groq judge.

```bash
export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-5.6-luna
export LLM_MAX_TOKENS=4000
export LLM_TIMEOUT_SECONDS=60

export SEMANTIC_LLM_PROVIDER=groq
export SEMANTIC_GROQ_MODEL=openai/gpt-oss-20b
export SEMANTIC_LLM_MAX_TOKENS=600
export SEMANTIC_LLM_TIMEOUT_SECONDS=30

uv run python -m autonomy_lab.semantic_judge_cli agent \
  --incident INC-001 \
  --json
```

The immediate output exposes non-secret generator/judge identity plus `self_judge`, while semantic calls and tokens remain separate from the generator pattern metrics.

A judge failure does not erase a successful generator run; the calibration command preserves the run and returns exit code `2` for judge configuration, rate-limit, provider, or schema failures.

## Reproducible Benchmark v1

Run repeated cycles across all six patterns and persist metadata-only experiment artifacts:

```bash
uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --run-interval-seconds 30 \
  --output results/groq-gpt-oss-20b-900
```

Each cycle contains all six patterns, but the starting pattern rotates deterministically across cycles. `--run-interval-seconds` pauses only between independent benchmark attempts; it does not serialize calls inside a pattern. There are no hidden retries.

The benchmark writes:

```text
results/groq-gpt-oss-20b-900/
├── runs.jsonl
├── summary.csv
└── summary.md
```

Artifacts contain provider/model/config metadata, execution metrics, deterministic grounding counts, reliability status, and successful trajectories. They intentionally exclude prompts, model answers, evidence bodies, tool arguments/results, claim text, semantic judgement text, and credentials.

The newer claim/semantic layers do **not** reclassify the historical 60-run benchmark dataset. They remain explicit post-run calibration surfaces until broader labelled evaluation is available.

See [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md).

## Grounding Evaluation v1

Grounding Evaluation v1 is deterministic and treats the bounded fixture as the source of truth.

It checks:

- semantic versions;
- timestamps;
- measurements, percentages and durations;
- exact percentage-point deltas derivable from fixture percentages;
- timestamp-to-measurement associations in supported Markdown table structures;
- strong causal language without explicit uncertainty or causal rejection;
- explicit preservation of uncertainty;
- proposal sections, where new time/measurement values are tracked as proposed parameters rather than observed facts.

It is intentionally **not** a universal hallucination detector. `100%` specific grounding means that the exact factual specifics checked by v1 were supported or derivable; it does not prove that every sentence is correct.

See [`docs/GROUNDING.md`](docs/GROUNDING.md).

## Agent authority boundary

The agent can call only five read-only tools:

```text
get_service_metrics
get_recent_deployments
get_dependencies
search_runbook
get_previous_incidents
```

Deterministic code enforces `max_steps=6`, `max_tool_calls=8`, the exact tool-name allowlist, and active-incident scope.

There is no shell, restart, rollback, configuration mutation, or production write tool. The model can recommend a reversible change to a human; recommendation is not executable authority.

## Metadata-only traces

```bash
uv run autonomy-lab \
  --trace-file traces/runs.jsonl \
  repeat agent --runs 5
```

Traces contain pattern, incident id, model/tool call counts, trajectory, token counts, and latency. They deliberately exclude prompts, model answers, evidence content, tool arguments/results, claims, semantic judgement text, and credentials.

## What this project does not claim

The current evidence does **not** establish that:

- agents are better than workflows;
- workflows are safer than agents;
- one provider/model is universally better than another;
- lower latency implies better reasoning;
- more model calls necessarily improve or harm grounding;
- `100%` specific grounding means a fully correct answer;
- `100%` merged semantic support is ground truth;
- agreement between two models proves correctness;
- results from one incident generalize to other domains or evidence shapes.

The current strongest evidence is architectural and methodological: control ownership changes what can vary, deterministic hard signals can remain authoritative, and semantic judgement can be added selectively without silently rewriting benchmark execution metrics.

## Next experiments

The next work should improve **generalization and evaluator calibration**, not simply repeat `INC-001` more times:

1. build a static human-labelled claim set covering facts, inferences, actions, unsupported claims, causal negation, causal assertion, association errors, and historical-context traps;
2. run a deterministic × semantic judge matrix to measure agreement, false upgrades, and false rejections;
3. add multiple incident fixtures with different true causal structures and inconclusive cases;
4. add provider-aware cost normalization while preserving raw provider token metadata;
5. add Anthropic repeated evidence when API credits are available;
6. consider a real remote evaluator/evidence boundary before introducing A2A/MCP infrastructure.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The retained gate checks lock consistency, Ruff lint/format, architecture boundaries, strict MyPy, Pytest/coverage, Bandit, and dependency vulnerabilities.

## Claude Skill

Only the project-specific `.claude/skills/incident-analysis/SKILL.md` is retained. Generic harness agents, hooks, MCP skills, and workflow scaffolding were removed because they are not runtime requirements for this case.

## Why `a2a-otel-kit` is still not wired in

There is still no real A2A/MCP/distributed-process boundary. Adding protocol infrastructure only for portfolio breadth would obscure the architecture comparison.

If a later phase moves the semantic judge, evidence provider, or another agent to a separate process/service, [`a2a-otel-kit`](https://github.com/brunovicco/a2a-otel-kit) becomes useful for W3C trace-context propagation and metadata-only OTLP spans.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — runtime architecture and boundaries
- [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md) — repeated benchmark methodology
- [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) — repeated OpenAI/Groq live evidence
- [`docs/GROUNDING.md`](docs/GROUNDING.md) — deterministic Grounding v1
- [`docs/CLAIM_EVALUATION.md`](docs/CLAIM_EVALUATION.md) — deterministic Claim Evaluation v2
- [`docs/SEMANTIC_CLAIM_EVALUATION.md`](docs/SEMANTIC_CLAIM_EVALUATION.md) — selective semantic escalation v2.1
- [`docs/SEMANTIC_JUDGE_DECOUPLING.md`](docs/SEMANTIC_JUDGE_DECOUPLING.md) — independent judge v2.2
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md) — provider configuration and references
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — development workflow

## References

- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [OpenAI — Responses API / reasoning](https://developers.openai.com/api/docs/guides/reasoning)
- [OpenAI — Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI — Models](https://developers.openai.com/api/docs/models)
- [OpenRouter — Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-models-router)
- [Groq — OpenAI Compatibility](https://console.groq.com/docs/openai)
- [Groq — Rate limits](https://console.groq.com/docs/rate-limits)
- [Claude Python Engineering Harness](https://github.com/brunovicco/claude-python-engineering-harness)
- [a2a-otel-kit](https://github.com/brunovicco/a2a-otel-kit)
