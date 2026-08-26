# Controlled Autonomy Lab

> Same incident. Different levels of LLM autonomy.

Controlled Autonomy Lab is a compact reference implementation for comparing six common LLM application architectures against the same production-incident fixture.

The experiment asks one question:

> Who owns the next step: deterministic application code or the model?

The repository focuses on control flow, evidence grounding, provider behavior, tool use and reproducible measurements rather than on framework-specific abstractions.

## The six patterns

The same incident is analyzed through six architectures inspired by Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents):

1. **Augmented LLM** — one model call with deterministic evidence augmentation.
2. **Prompt chaining** — deterministic application code owns a multi-stage sequence.
3. **Routing** — a model chooses a bounded route; application code executes the selected branch.
4. **Parallelization** — independent model calls fan out concurrently and deterministic code synthesizes the result.
5. **Evaluator-optimizer** — one model drafts and another evaluates/refines inside a bounded loop.
6. **Bounded tool-using agent** — the model chooses which read-only evidence tool to call next, inside hard step/tool budgets.

The point is not to declare one architecture universally superior. The lab makes their trade-offs measurable.

## Incident fixture

All patterns investigate the same fixture, `INC-001`, for `checkout-api`:

- HTTP 5xx increases from `0.2%` to `8.7%`;
- p95 latency increases from `310 ms` to `2840 ms`;
- deployment `v2.18.4` occurred shortly before the incident;
- payment-provider latency increased shortly after `14:00`;
- there is no confirmed dependency outage;
- the runbook explicitly warns that correlation is not proof of causality.

The fixture is intentionally small and bounded so architectural differences are easier to observe.

## Agent boundaries

The bounded agent can only call these read-only tools:

```text
get_service_metrics
get_recent_deployments
get_dependencies
search_runbook
get_previous_incidents
```

Hard limits:

```text
max_steps = 6
max_tool_calls = 8
```

The agent cannot execute shell commands, restart services, rollback deployments, mutate configuration or write to production systems.

## Provider-neutral runtime

The application layer depends on provider-neutral text/tool-use ports. Provider transport remains in adapters.

Supported providers:

```text
anthropic
openai
groq
openrouter
custom
```

OpenAI uses the native **Responses API** for both text and tool-use calls. The adapter sets `store=false`; during a bounded agent run it keeps returned Responses output items only in memory so opaque reasoning items can be replayed with subsequent function outputs. This preserves reasoning continuity without placing provider-specific state in the domain model or persisting prompts/model output in benchmark artifacts.

Groq, OpenRouter and custom OpenAI-compatible endpoints continue to use the generic Chat Completions adapter. Anthropic uses the native Messages API adapter.

Example environment:

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=...
export GROQ_MODEL=openai/gpt-oss-20b
export LLM_MAX_TOKENS=1200
export LLM_TIMEOUT_SECONDS=30
```

Provider failures are normalized to `ModelProviderError`; HTTP 429 becomes `ModelRateLimitError` with a safe `Retry-After` hint when available. Provider error details are bounded and sanitized before they can enter benchmark metadata.

No adapter performs automatic retries. Hidden retries would change latency and quota behavior and therefore distort the experiment.

## Architecture

```text
src/autonomy_lab/
├── domain/
│   ├── autonomy.py         # provider-neutral run contracts
│   ├── benchmark.py        # benchmark records and summaries
│   └── grounding.py        # deterministic grounding result types
├── application/
│   ├── model_ports.py      # common text + tool-use model boundary
│   ├── model_errors.py     # provider-neutral error contract
│   ├── benchmark.py        # repeated benchmark orchestration
│   ├── grounding.py        # fixture-backed grounding evaluator
│   └── patterns/           # six autonomy patterns
├── adapters/
│   ├── anthropic.py
│   ├── openai_responses.py # native OpenAI Responses transport
│   ├── openai_compatible.py
│   ├── providers.py        # environment composition/presets
│   ├── incidents.py
│   ├── benchmark_artifacts.py
│   ├── benchmark_metadata.py
│   └── run_log.py
└── cli.py                  # command-line interface
```

The project started from [`claude-python-engineering-harness`](https://github.com/brunovicco/claude-python-engineering-harness), but generic scaffold not used by this case has been removed. The deterministic quality runner and architecture validator were retained because they still enforce project behavior.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run and compare

One pattern:

```bash
uv run autonomy-lab run augmented --incident INC-001
```

One pattern with deterministic grounding findings:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding
```

Structured result including grounding:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding --json
```

All patterns:

```bash
uv run autonomy-lab compare --incident INC-001
```

`compare` reports execution metrics plus `unsupported`, `proposed`, `causality`, `uncertainty`, and `status` for every architecture. If one pattern is rate-limited or hits another provider error, completed rows are preserved and the remaining patterns still run. The command returns exit code `2` when the comparison is partial.

Trajectory variance:

```bash
uv run autonomy-lab repeat agent --incident INC-001 --runs 5
```

Live runs can consume quota or paid tokens depending on the selected provider.

## Reproducible Benchmark v1

Run repeated cycles across all six patterns and persist the experiment:

```bash
uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --run-interval-seconds 30 \
  --output results/groq-gpt-oss-20b-900
```

The `30s` interval above is a conservative starting point for the currently documented Groq Free Plan limits of `openai/gpt-oss-20b`; provider/account limits can differ and change over time. In live smoke calibration on 2026-08-26 with `LLM_MAX_TOKENS=900`, a `2s` interval completed `2/6` patterns while `30s` completed `6/6` with exit code `0`. Those smoke runs are pacing calibration with `n=1`, not architecture-quality conclusions.

Each cycle contains all six patterns, but the starting pattern rotates deterministically on later cycles. This reduces fixed-order exposure to provider quota drift without introducing random ordering.

`--run-interval-seconds` pauses only **between benchmark attempts**. It does not serialize calls inside a pattern, so `parallel` remains concurrent and chaining/evaluator/agent retain their original multi-call behavior. There are no hidden retries.

The benchmark writes:

```text
results/groq-gpt-oss-20b-900/
├── runs.jsonl
├── summary.csv
└── summary.md
```

The artifacts contain provider/model/configuration metadata, execution metrics, deterministic grounding counts, reliability status and successful trajectories. They remain metadata-only: prompts, model answers, evidence bodies, tool arguments/results and credentials are excluded.

Existing benchmark files are protected by default. Use `--overwrite` only when replacement is intentional.

A complete benchmark returns exit code `0`. If one or more attempts are rate-limited or fail at the provider boundary, remaining attempts continue, partial artifacts are preserved, and the command returns `2`.

See [`docs/BENCHMARKING.md`](docs/BENCHMARKING.md) for methodology, output schema, pacing semantics, aggregation rules and limitations.

## Grounding Evaluation v1

Grounding Evaluation v1 is deterministic: it does not call another LLM and treats the bounded incident fixture as the source of truth.

It currently checks:

- semantic versions;
- timestamps;
- measurements, percentages and durations;
- exact percentage-point deltas derivable from fixture percentages;
- timestamp-to-measurement associations in supported Markdown table structures;
- strong causal language without a local or section-level uncertainty qualifier;
- explicit uncertainty language;
- proposal sections so proposed operational thresholds are not mislabeled as factual claims;
- supported historical causal context.

The evaluator deliberately remains narrow. It is not a general semantic fact checker or NLI model.

See [`docs/GROUNDING.md`](docs/GROUNDING.md).

## Metadata-only observability

Optional traces record only run metadata such as:

```text
pattern
incident_id
model_calls
tool_calls
steps
token counts
latency
```

Prompts, answers, evidence bodies, tool arguments/results and credentials are deliberately excluded.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The gate checks lock consistency, Ruff lint/format, architecture rules, MyPy, Pytest with coverage, Bandit and dependency vulnerabilities.

## What this lab is for

The project is designed as a small empirical case for reasoning about questions such as:

- How much additional latency and token use does extra autonomy introduce?
- Does a more autonomous architecture produce better-grounded answers?
- Does parallel fan-out reduce latency enough to justify extra tokens?
- Does evaluator-optimizer actually improve factual quality?
- Does an agent gather enough evidence before answering?
- How often do providers fail or rate-limit different architectural shapes?
- Does the model preserve uncertainty or overstate causality?

The intent is to replace architecture-by-fashion with architecture-by-evidence.
