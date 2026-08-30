# Desenvolvimento

> **Idioma:** Português (Brasil) · [Original em inglês](../DEVELOPMENT.md)

## Setup

```bash
uv sync --frozen --all-groups
```

O runtime intencionalmente não possui dependências de terceiros. As dependências de desenvolvimento fornecem linting, typing, testes, security scanning e auditoria de dependências.

## Quality gate

```bash
uv run python scripts/quality_gate.py
```

O gate executa:

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

O validador de arquitetura e o quality runner se originaram em `claude-python-engineering-harness` e permanecem porque oferecem valor determinístico a este projeto. Validadores genéricos de MCP/governança e scaffolding de runtime não utilizado foram removidos.

## Desenvolvimento de providers

Mantenha os padrões da aplicação neutros em relação ao provider. Adicione serialização específica do provider em `adapters/` e exponha-a por `adapters/providers.py` somente quando ela satisfizer as duas portas de modelo exigidas pela CLI.

Um novo provider deve ter testes para:

- mapeamento de resposta textual;
- mapeamento de uso de tokens;
- redação de erros HTTP/provider;
- mapeamento de tool calls, caso o agente seja suportado;
- configuração ausente/inválida.

Não adicione um SDK de provider apenas para reduzir uma pequena quantidade de código de serialização. Uma nova dependência deve justificar a abstração que introduz.

## Configuração

`.env.example` documenta as variáveis suportadas, mas não é carregado automaticamente. Nunca faça commit de chaves de providers. Use variáveis de ambiente exportadas ou um mecanismo externo de secrets.

## Suporte específico do projeto para Claude Code

A única Skill preservada é `.claude/skills/incident-analysis/SKILL.md`. Ela é apenas ergonomia opcional de desenvolvimento, não uma dependência de runtime.
