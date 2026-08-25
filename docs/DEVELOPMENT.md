# Development

## Setup

```bash
uv sync --frozen --all-groups
```

The runtime intentionally has no third-party dependencies. Development dependencies provide linting, typing, tests, security scanning and dependency auditing.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

The gate runs:

```text
uv lock --check
ruff check .
ruff format --check .
architecture validation
mypy
pytest + coverage
bandit
pip-audit
```

The architecture validator and quality runner originated in `claude-python-engineering-harness` and remain because they provide deterministic value to this project. Generic MCP/governance validators and unused runtime scaffolding were removed.

## Provider development

Keep application patterns provider-neutral. Add provider-specific serialization under `adapters/` and expose it through `adapters/providers.py` only when it satisfies both model ports required by the CLI.

A new provider must have tests for:

- text response mapping;
- token-usage mapping;
- HTTP/error redaction;
- tool-call mapping if the agent is supported;
- missing/invalid configuration.

Do not add a provider SDK just to reduce a small amount of serialization code. A new dependency should justify the abstraction it introduces.

## Configuration

`.env.example` documents supported variables but is not auto-loaded. Never commit provider keys. Use exported environment variables or an external secret mechanism.

## Project-specific Claude Code support

The only retained Skill is `.claude/skills/incident-analysis/SKILL.md`. It is optional development ergonomics, not a runtime dependency.
