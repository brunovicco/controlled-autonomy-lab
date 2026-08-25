# Controlled Autonomy Lab

> Same incident. Different levels of LLM autonomy. Multiple providers.

Controlled Autonomy Lab is a small Python reference implementation for comparing six architectures on the same production incident:

1. Augmented LLM
2. Prompt chaining
3. Routing
4. Parallelization
5. Evaluator-optimizer
6. Bounded tool-using agent

The goal is not to prove that agents are better. It is to make the delegation boundary observable: **who owns the next step, deterministic application code or the model?**

## Provider support

The architecture is provider-neutral. The project includes two transport adapters:

- native Anthropic Messages API;
- OpenAI-compatible Chat Completions + function calling.

Presets are available for:

| Provider | `LLM_PROVIDER` | Default model | Cost path |
| --- | --- | --- | --- |
| Anthropic | `anthropic` | `claude-sonnet-5` | paid API |
| OpenAI | `openai` | `gpt-5.6-luna` | paid API |
| Groq | `groq` | `openai/gpt-oss-20b` | Free Plan available |
| OpenRouter | `openrouter` | `openrouter/free` | free router |
| Custom OpenAI-compatible | `custom` | user-defined | provider-dependent |

**Recommended zero-cost starting point:** OpenRouter's `openrouter/free`. It routes requests among currently available free models. Availability, rate limits, model selection, and provider policies can change over time, so free access is intentionally configuration rather than a project invariant.

Groq is a second free-to-start option through its Free Plan. For the agent pattern, use a model/provider combination that supports tool/function calling.

See [`docs/PROVIDERS.md`](docs/PROVIDERS.md) for setup details and official provider references.

## Quick start with a free provider

Requirements: Python 3.13/3.14 and `uv`.

```bash
uv sync --frozen --all-groups

export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL=openrouter/free

uv run python -m harness_example.entrypoints.autonomy_cli \
  run augmented --incident INC-001
```

Try the bounded agent with the same provider configuration:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli \
  run agent --incident INC-001
```

Or use Groq's Free Plan:

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY="..."
export GROQ_MODEL=openai/gpt-oss-20b
```

`.env.example` is a reference file; the application intentionally does not auto-load `.env` files or add a dotenv dependency. Export variables in your shell or use your preferred secret/configuration mechanism.

## Switch providers without changing application code

Anthropic:

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY="..."
export CLAUDE_MODEL=claude-sonnet-5
```

OpenAI:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_MODEL=gpt-5.6-luna
```

Any compatible HTTPS endpoint:

```bash
export LLM_PROVIDER=custom
export OPENAI_COMPAT_API_KEY="..."
export OPENAI_COMPAT_BASE_URL="https://provider.example/v1"
export OPENAI_COMPAT_MODEL="provider-model"
```

The custom adapter expects compatible `/chat/completions` semantics and function/tool calling for the agent pattern.

## The common incident

Every pattern receives `INC-001`:

- service: `checkout-api`;
- HTTP 5xx rises from `0.2%` to `8.7%`;
- p95 latency rises from `310ms` to `2840ms`;
- `v2.18.4` was deployed seven minutes before the incident;
- an upstream payment provider also shows increased latency.

The fixture creates correlation without proving causality. Good output should distinguish observed facts from hypotheses.

## Control model

| Pattern | Who owns the path? | Model calls | Tool use | Main guard |
| --- | --- | ---: | ---: | --- |
| Augmented LLM | application | 1 | no | one bounded call |
| Chaining | application | 3 | no | fixed handoffs |
| Routing | application + classifier | 2 | no | route allowlist |
| Parallelization | application | 4 | no | fixed fan-out/fan-in |
| Evaluator-optimizer | application | variable | no | schema + revision budget |
| Agent | model | variable | yes | tool allowlist + step/tool budgets |

## Architecture

```text
src/harness_example/
├── domain/                 # provider-neutral contracts
├── application/
│   ├── model_ports.py      # common text + tool-use model boundary
│   └── patterns/           # six autonomy patterns
├── adapters/
│   ├── anthropic.py
│   ├── openai_compatible.py
│   ├── providers.py        # environment composition/presets
│   ├── incidents.py
│   └── run_log.py
└── entrypoints/
    └── autonomy_cli.py
```

The project started from [`claude-python-engineering-harness`](https://github.com/brunovicco/claude-python-engineering-harness), but generic scaffold not used by this case has been removed. The deterministic quality runner and architecture validator were retained because they still enforce project behavior.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run and compare

One pattern:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli run augmented --incident INC-001
```

All patterns:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli compare --incident INC-001
```

Trajectory variance:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli repeat agent --incident INC-001 --runs 5
```

Live runs can consume quota or paid tokens depending on the selected provider.

## Agent authority boundary

The agent can call only five read-only tools:

```text
get_service_metrics
get_recent_deployments
get_dependencies
search_runbook
get_previous_incidents
```

Deterministic code enforces `max_steps=6`, `max_tool_calls=8`, the exact tool-name allowlist and active-incident scope. There is no shell, restart, rollback, configuration mutation, or production write tool.

## Metadata-only traces

```bash
uv run python -m harness_example.entrypoints.autonomy_cli \
  --trace-file traces/runs.jsonl \
  repeat agent --runs 5
```

The trace contains pattern, incident id, model/tool call counts, trajectory, token counts and latency. It deliberately excludes prompts, model answers, evidence content, tool arguments/results and credentials.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The retained gate checks lock consistency, Ruff, formatting, architecture boundaries, Mypy, Pytest/coverage, Bandit and dependency vulnerabilities.

## Claude Skill

Only the project-specific `.claude/skills/incident-analysis/SKILL.md` is retained. Generic harness agents, hooks, MCP skills and workflow scaffolding were removed because they are not runtime requirements for this case.

## Why `a2a-otel-kit` is still not wired in

There is still no real A2A/MCP/distributed-process boundary. Adding protocol infrastructure now would obscure the architecture comparison. If a later phase moves the evaluator, evidence provider or another agent to a separate process, [`a2a-otel-kit`](https://github.com/brunovicco/a2a-otel-kit) becomes useful for W3C trace-context propagation and metadata-only OTLP spans.

## References

- [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic — Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [OpenAI — Models](https://developers.openai.com/api/docs/models)
- [OpenRouter — Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-models-router)
- [Groq — OpenAI Compatibility](https://console.groq.com/docs/openai)
- [Groq — Rate limits](https://console.groq.com/docs/rate-limits)
- [Claude Python Engineering Harness](https://github.com/brunovicco/claude-python-engineering-harness)
- [a2a-otel-kit](https://github.com/brunovicco/a2a-otel-kit)
