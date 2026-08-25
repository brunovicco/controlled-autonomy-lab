---
name: incident-analysis
description: Run and compare the controlled-autonomy incident-analysis patterns without changing runtime permissions.
argument-hint: "[pattern|compare|repeat] [optional incident id]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

Operate the Controlled Autonomy Lab for:

$ARGUMENTS

Before running anything:

1. Read `README.md`, `docs/ARCHITECTURE.md` and `docs/PROVIDERS.md`.
2. Keep `INC-001` as the default unless the user names another fixture.
3. Never print, read back or persist any provider API key.
4. Do not modify tool permissions, step budgets, retry budgets or evidence fixtures merely to obtain a preferred answer.
5. Treat deployment timing and dependency latency as hypotheses unless available evidence proves causality.

Use the existing CLI:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli ...
```

Use the provider already selected through `LLM_PROVIDER`; do not silently switch providers during a comparison.

For `compare`, explain model calls, tool calls, token counts, latency and control-flow ownership. For `repeat`, report unique trajectories and call out whether the model-controlled path changed across runs.

Do not mutate production systems or add A2A/MCP infrastructure unless the user explicitly asks for a real distributed boundary.
