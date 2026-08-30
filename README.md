# Controlled Autonomy Lab

> Same control patterns. Different evidence postures. Multiple providers.

Controlled Autonomy Lab is a small Python reference implementation for comparing six LLM application architectures across bounded production-incident fixtures with different evidence postures.

The central question is not whether agents are better than workflows. It is:

> **Who owns the next step: deterministic application code or the model?**

The lab makes that delegation boundary observable through execution topology, tool use, latency, token usage, deterministic grounding, claim-level evaluation, causal-authority checks, and selective semantic judgement.

## What this case demonstrates

The same incident-analysis task can be implemented with six different control patterns:

1. Augmented LLM
2. Prompt chaining
3. Routing
4. Parallelization
5. Evaluator-optimizer
6. Bounded tool-using agent

The project evaluates the resulting behavior through progressively stronger—but deliberately separate—layers:

```text
pattern execution
      ↓
Grounding Evaluation v1
exact specifics, associations, causal discipline
      ↓
Epistemic Evaluation v4.1
evidence posture and causal-authority alignment
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

### Frozen repeated architecture benchmark

The repeated benchmark holds `INC-001` constant and measures repeated behavior across all six architecture patterns and three provider/model/configuration bundles.

```text
1 incident × 6 patterns × 5 runs × 3 provider bundles = 90 executions
```

All **90/90 executions completed successfully**.

Specific grounding by pattern:

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | 95.3% |
| Chaining | 90.0% | 67.4% | 82.1% |
| Routing | 100.0% | 87.8% | 84.6% |
| Parallel | 92.8% | 87.1% | 94.8% |
| Evaluator-optimizer | 100.0% | 88.5% | 96.7% |
| Agent | 100.0% | 82.6% | 93.6% |

The strongest repeated-benchmark observations are:

- chaining had the lowest specific-grounding ratio in all three provider bundles;
- evaluator-optimizer remained competitive on grounding;
- additional model calls did not monotonically improve grounding;
- agent execution topology depended on the provider/model bundle;
- OpenAI and Anthropic agents showed one coarse trajectory, while Groq produced four;
- high specific grounding did not guarantee causal discipline.

These are **provider/model/API/configuration bundle** results, not a pure model leaderboard.

See [`docs/FROZEN_THREE_PROVIDER_BENCHMARK.md`](docs/FROZEN_THREE_PROVIDER_BENCHMARK.md) for the full frozen 90-run analysis.

### Multi-incident breadth benchmark

The breadth experiment changes the evidence posture while keeping the six architecture patterns fixed:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

Main generation:

- **72 attempted cells**;
- **59 successful cells**;
- **12 Groq rate-limited cells**;
- **1 Anthropic provider-error cell**;
- quality metrics calculated only on `status=ok` cells;
- provider failures preserved as availability evidence rather than imputed quality zeros.

Architecture-level observed results:

| Pattern | Observed | Mean grounding | Causal overclaims |
| --- | ---: | ---: | ---: |
| Augmented | 10/12 | 97.8% | 3 |
| Chaining | 9/12 | 74.4% | 5 |
| Routing | 10/12 | 92.8% | 2 |
| Parallel | 10/12 | 94.9% | 7 |
| Evaluator-optimizer | 10/12 | 97.6% | 4 |
| Agent | 10/12 | 95.4% | **0** |

The most important breadth observations are:

- the bounded tool-using agent was the only pattern with zero detected causal overclaims across every observable cell;
- chaining showed the weakest overall grounding/cost trade-off;
- parallelization maintained high grounding but produced the most causal overclaims and the largest token footprint;
- evaluator-optimizer sometimes revised its output, but an internal quality pass did not guarantee external causal correctness;
- routing exposed provider/model-dependent control-flow selection;
- specific grounding and causal authority remained separate evaluation dimensions;
- lexical uncertainty-language detection saturated across all successful cells and is therefore not treated as proof of epistemic correctness.

The result is **not** “agents win.” It supports the narrower hypothesis that bounded autonomy may help a system acquire evidence dynamically while operating inside explicit tool, action, and execution limits.

See:

- [`docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md`](docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md) for experiment design and frozen execution boundaries;
- [`docs/MULTI_INCIDENT_BREADTH_RESULTS.md`](docs/MULTI_INCIDENT_BREADTH_RESULTS.md) for the full frozen analysis, threats to validity, and explicit non-claims;
- [`results/breadth-main/`](results/breadth-main/) for the curated metadata-only evidence pack and SHA-256 checksums.

### Epistemic posture benchmark

A new frozen generation evaluates whether final-answer causal authority matches the evidence posture:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

The generation produced **70 successful cells**, with one Groq rate-limited cell and one Groq provider-error cell preserved as availability evidence.

Epistemic v4.1 verdicts across successful cells were:

| Verdict | Count | Share |
| --- | ---: | ---: |
| Aligned | 20 | 28.6% |
| Overclaimed | 41 | 58.6% |
| No-position | 6 | 8.6% |
| Over-hedged | 3 | 4.3% |

`INC-001` and `INC-004`, the two fixtures requiring the greatest causal restraint, accounted for **29/41 detected overclaims (~70.7%)**. Among the fully observed patterns, the bounded tool-using agent had the lowest detected-overclaim rate in this generation at **4/12 (33.3%)**.

These are deterministic **detected verdicts under Epistemic v4.1**, not proof of semantic causal error. The result does not establish that agents are universally safer or better.

See:

- [`docs/EPISTEMIC_EVALUATION.md`](docs/EPISTEMIC_EVALUATION.md) for evaluator semantics and limitations;
- [`docs/EPISTEMIC_GENERATION_V2_RESULTS.md`](docs/EPISTEMIC_GENERATION_V2_RESULTS.md) for the frozen analysis and non-claims;
- [`results/epistemic-v4-1-main/`](results/epistemic-v4-1-main/) for the metadata-only evidence pack and SHA-256 checksums.

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

Semantic Claim Evaluation v2.1 therefore evaluates only eligible conservative misses. Live calibration reduced semantic work after current-incident facts were moved back into deterministic high-confidence matching.

The remaining historical-context paraphrase required semantic entailment and was upgraded without weakening the Grounding v1 hard-failure rule.

See [`docs/SEMANTIC_CLAIM_EVALUATION.md`](docs/SEMANTIC_CLAIM_EVALUATION.md).

### Generator × judge decoupling

Semantic Judge Decoupling v2.2 separates answer generation from semantic judgement.

Two bounded-agent smokes used an OpenAI generator and Groq judge with `self_judge=false`. They validate the **routing and authority architecture**, not judge accuracy or ground truth.

See [`docs/SEMANTIC_JUDGE_DECOUPLING.md`](docs/SEMANTIC_JUDGE_DECOUPLING.md).

## Incident fixtures

`INC-001` remains the baseline incident used by the repeated architecture benchmark.

It describes `checkout-api` with:

- HTTP 5xx rising from `0.2%` to `8.7%`;
- p95 latency rising from `310ms` to `2840ms`;
- deployment `v2.18.4` at `13:58` with a new payment-provider timeout configuration;
- increased payment-provider latency shortly after `14:00`;
- no confirmed provider outage;
- historical incident context that is not evidence of the current root cause.

The fixture intentionally creates correlation without proving current causality.

The multi-incident breadth benchmark adds three contrasting evidence postures:

| Incident | Evidence posture |
| --- | --- |
| `INC-001` | correlation without proven current cause |
| `INC-002` | deployment cause explicitly confirmed |
| `INC-003` | dependency cause explicitly confirmed |
| `INC-004` | inconclusive evidence requiring abstention |

The four fixtures test whether architecture behavior changes when the system is allowed to infer a cause, required to preserve uncertainty, or expected to abstain.

Good output must distinguish observed facts, supported causal conclusions, hypotheses, historical context, and reversible recommendations.

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
├── domain/                              # provider-neutral contracts
├── application/
│   ├── benchmark.py                    # benchmark orchestration
│   ├── grounding.py                    # deterministic grounding
│   ├── claim_evaluation.py             # deterministic claim classification
│   ├── semantic_claim_evaluation.py    # selective semantic merge
│   └── patterns/                       # six autonomy patterns
├── adapters/
│   ├── anthropic.py                    # native Anthropic Messages
│   ├── openai_responses.py             # native OpenAI Responses
│   ├── openai_compatible.py            # Groq/OpenRouter/custom
│   ├── providers.py                    # generator + judge composition
│   ├── incidents.py                    # bounded incident fixtures
│   └── benchmark_metadata.py
├── cli.py
└── semantic_judge_cli.py
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

Provider-specific reasoning state does not enter the domain model or benchmark artifacts.

See [`docs/PROVIDERS.md`](docs/PROVIDERS.md).

## Quick start

Requirements: Python 3.13/3.14 and `uv`.

```bash
uv sync --frozen --all-groups
```

Free-provider example with Groq:

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

Grounding + deterministic claims:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims \
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

## Reproducible benchmarks

Repeated benchmark:

```bash
uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --run-interval-seconds 30 \
  --output results/repeated-<provider>
```

Multi-incident breadth benchmark:

```bash
uv run autonomy-lab benchmark \
  --all-incidents \
  --runs 1 \
  --run-interval-seconds 30 \
  --output results/breadth-<provider>
```

Each benchmark rotates pattern order deterministically. There are no hidden retries.

Artifacts contain provider/model/config metadata, execution metrics, deterministic grounding counts, reliability status, and successful trajectories. They intentionally exclude prompts, model answers, evidence bodies, tool arguments/results, claim text, semantic judgement text, and credentials.

See [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md).

## Grounding Evaluation v1

Grounding Evaluation v1 is deterministic and treats the bounded fixture as the source of truth.

It checks semantic versions, timestamps, measurements, supported associations, strong causal language, explicit uncertainty/rejection, and proposed parameters.

It is intentionally **not** a universal hallucination detector. `100%` specific grounding means that the factual specifics checked by v1 were supported or derivable; it does not prove that every sentence is correct.

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
- zero detected causal overclaims proves universal causal correctness;
- agreement between two models proves correctness;
- breadth results from four bounded fixtures generalize to other domains, systems, or evidence shapes.

The strongest current evidence is architectural and methodological: control ownership changes what can vary, evidence posture changes where causal failures appear, deterministic hard signals can remain authoritative, and semantic judgement can be added selectively without silently rewriting benchmark execution metrics.

## Next experiments

The next work should improve evaluator discrimination and external validity rather than silently expanding the current generation:

1. calibrate Epistemic v4.1 against a larger static labelled posture corpus before adding semantic escalation;
2. add repeated runs to selected breadth cells to measure variance without mixing generations;
3. add provider-aware cost normalization while preserving raw provider token metadata;
4. expand incident fixtures only as new frozen experiment generations;
5. consider a real remote evaluator/evidence boundary before introducing A2A/MCP infrastructure.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The retained gate checks lock consistency, Ruff lint/format, architecture boundaries, strict MyPy, Pytest/coverage, Bandit, and dependency vulnerabilities.

## Why `a2a-otel-kit` is still not wired in

There is still no real A2A/MCP/distributed-process boundary. Adding protocol infrastructure only for portfolio breadth would obscure the architecture comparison.

If a later phase moves the semantic judge, evidence provider, or another agent to a separate process/service, [`a2a-otel-kit`](https://github.com/brunovicco/a2a-otel-kit) becomes useful for W3C trace-context propagation and metadata-only OTLP spans.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — runtime architecture and boundaries
- [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md) — benchmark methodology
- [`docs/FROZEN_THREE_PROVIDER_BENCHMARK.md`](docs/FROZEN_THREE_PROVIDER_BENCHMARK.md) — frozen 90-run repeated benchmark
- [`docs/MULTI_INCIDENT_FIXTURES.md`](docs/MULTI_INCIDENT_FIXTURES.md) — contrasting incident fixtures
- [`docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md`](docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md) — breadth experiment design and freeze
- [`docs/MULTI_INCIDENT_BREADTH_RESULTS.md`](docs/MULTI_INCIDENT_BREADTH_RESULTS.md) — frozen 72-cell breadth analysis
- [`docs/GROUNDING.md`](docs/GROUNDING.md) — deterministic Grounding v1
- [`docs/CLAIM_EVALUATION.md`](docs/CLAIM_EVALUATION.md) — deterministic Claim Evaluation v2
- [`docs/CLAIM_JUDGE_MATRIX.md`](docs/CLAIM_JUDGE_MATRIX.md) — labelled deterministic/judge matrix
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
