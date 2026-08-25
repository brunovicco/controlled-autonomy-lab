@AGENTS.md

# Claude Code-specific behavior

- Start by reading `README.md`, `docs/ARCHITECTURE.md`, relevant code, and tests.
- Preserve the central comparison: the same incident must remain usable across every architecture pattern.
- Keep workflow control flow deterministic; do not silently turn a workflow into an agent loop.
- Keep agent tools read-only and narrow. New tools require an explicit threat/authority review.
- Never raise `max_steps`, `max_tool_calls`, or evaluator retry limits merely to hide a failing test.
- Do not log prompts, model answers, evidence bodies, tool arguments/results, or credentials.
- Prefer direct architectural primitives over framework abstractions unless measurement justifies the abstraction.
- For non-trivial changes, produce a brief plan before editing.
- Use specialized project agents when their scope matches the task.
- Use `/quality-gate` before declaring implementation complete.
- Use `/security-review` for tool changes, external inputs, credentials, or new network boundaries.
- Prefer small, reviewable diffs. Do not refactor unrelated code.
- Do not commit, push, merge, publish, deploy, or change infrastructure without an explicit user request.
- Treat generated code as untrusted until it passes review and automated checks.
- Never read or expose secrets. Use environment-variable names instead of values.
- Use MCP only for an actual approved external boundary; do not add it for demonstration value alone.
