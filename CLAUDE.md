# Claude Code project guidance

- Read `README.md`, `docs/ARCHITECTURE.md`, `docs/PROVIDERS.md`, relevant code and tests before non-trivial changes.
- Preserve the central comparison: the same incident must remain usable across every architecture pattern and provider.
- Keep workflow control flow deterministic; do not silently turn a workflow into an agent loop.
- Keep provider-specific serialization inside `adapters/`.
- Keep agent tools read-only and narrow. New tools require an explicit authority/security review.
- Never raise `max_steps`, `max_tool_calls` or evaluator retry limits merely to hide a failure.
- Do not log prompts, model answers, evidence bodies, tool arguments/results or credentials.
- Prefer direct architectural primitives over framework abstractions unless measurement justifies the abstraction.
- Run `uv run python scripts/quality_gate.py` before declaring implementation complete.
- Prefer small, reviewable diffs and do not refactor unrelated code.
- Never read or expose secrets. Use environment-variable names instead of values.
- Add A2A/MCP only for a real distributed boundary, not for demonstration value alone.
