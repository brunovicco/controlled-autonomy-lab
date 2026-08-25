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

1. Read `README.md` and `docs/ARCHITECTURE.md`.
2. Keep `INC-001` as the default unless the user names another fixture.
3. Never print, read back, or persist `ANTHROPIC_API_KEY`.
4. Do not modify tool permissions, step budgets, retry budgets, or evidence fixtures merely to obtain a preferred answer.
5. Treat deployment timing and dependency latency as hypotheses unless the available evidence proves causality.

Use the existing CLI rather than recreating pattern logic in shell commands:

```bash
uv run python -m harness_example.entrypoints.autonomy_cli ...
```

For `compare`, explain model calls, tool calls, token counts, latency, and control-flow ownership.
For `repeat`, report unique trajectories and call out whether the model-controlled path changed across runs.

Do not mutate production systems, call external tools other than the configured Claude API through the application, or add A2A/MCP infrastructure unless the user explicitly asks to create a real distributed boundary.
