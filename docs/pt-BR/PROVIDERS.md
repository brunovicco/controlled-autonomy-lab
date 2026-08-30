# Providers de LLM

> **Idioma:** Português (Brasil) · [Original em inglês](../PROVIDERS.md)

O Controlled Autonomy Lab mantém o transporte específico de provider fora dos padrões da aplicação. Trocar de provider não deve alterar a topologia do workflow, a autoridade do agente ou as regras de evidência.

## Seleção

Defina `LLM_PROVIDER` como um dos valores:

```text
anthropic
openai
groq
openrouter
custom
```

Limites compartilhados opcionais:

```bash
export LLM_MAX_TOKENS=1200
export LLM_TIMEOUT_SECONDS=30
```

## OpenRouter — ponto de partida gratuito recomendado

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL=openrouter/free
```

`openrouter/free` é um router sobre modelos gratuitos, não um único modelo fixado. Isso torna o lab acessível sem inferência paga, mas também significa que o modelo subjacente pode variar. Isso deve ser lembrado ao comparar latência, qualidade ou variação de trajetória.

A OpenRouter documenta que o free router filtra os modelos gratuitos disponíveis conforme os recursos exigidos pela requisição, incluindo tool calling quando necessário. Disponibilidade gratuita e limites são controlados pelo provider e podem mudar.

Documentação oficial:
- https://openrouter.ai/docs/guides/routing/routers/free-models-router
- https://openrouter.ai/pricing

## Groq — alternativa no Free Plan

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY="..."
export GROQ_MODEL=openai/gpt-oss-20b
```

O preset usa a base URL da Groq compatível com OpenAI. A Groq publica rate limits separados por modelo para o Free Plan. O modelo default pode ser substituído sem mudança de código.

Documentação oficial:
- https://console.groq.com/docs/openai
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/tool-use/overview

## Anthropic

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY="..."
export CLAUDE_MODEL=claude-sonnet-5
```

Anthropic usa seu adapter nativo da Messages API em vez do adapter compatível com OpenAI.

Documentação oficial:
- https://platform.claude.com/docs/en/api/messages/create
- https://platform.claude.com/docs/en/about-claude/models/overview

## OpenAI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_MODEL=gpt-5.6-luna
```

O preset OpenAI usa a Responses API nativa tanto para turnos somente de texto quanto para turnos com ferramentas. Isso permite que reasoning models usem function tools sem desabilitar reasoning.

O adapter envia `store=false`. Durante uma execução limitada do agente, os itens de output retornados pela Responses API são mantidos apenas em memória de processo para que itens opacos de reasoning possam ser reproduzidos junto com itens posteriores de `function_call_output`. Estado de reasoning específico do provider não entra no modelo de domínio nem nos artefatos de benchmark.

Documentação oficial:
- https://developers.openai.com/api/docs/guides/reasoning
- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/models

## Endpoint customizado compatível com OpenAI

```bash
export LLM_PROVIDER=custom
export OPENAI_COMPAT_API_KEY="..."
export OPENAI_COMPAT_BASE_URL="https://provider.example/v1"
export OPENAI_COMPAT_MODEL="provider-model"
```

A base URL deve usar HTTPS e não pode conter credenciais embutidas, query ou fragment. O adapter adiciona `/chat/completions`.

Padrões somente de texto exigem semântica compatível com Chat Completions. O agente exige adicionalmente function/tool calling no estilo OpenAI. Um provider que aceite chat básico, mas não tool calls, ainda pode ser usado com `augmented`, `chaining`, `routing`, `parallel` e `evaluator-optimizer`, mas não necessariamente com `agent`.

## Comparações justas

Trocar de provider envolve mais do que alterar o nome do modelo. Para comparações úteis:

1. fixe um modelo concreto em vez de um router quando reprodutibilidade importar;
2. mantenha o mesmo fixture de incidente e a mesma configuração dos padrões;
3. mantenha `LLM_MAX_TOKENS` e budgets constantes quando esse limite tiver semântica comparável; documente diferenças específicas do provider quando não tiver;
4. repita padrões estocásticos/controlados pelo modelo mais de uma vez;
5. registre traces metadata-only para comparar chamadas de modelo, chamadas de ferramentas, uso de tokens, latência e trajetória;
6. não interprete diferenças na contabilização de tokens dos providers como unidades de cobrança perfeitamente equivalentes.

Nenhum SDK de provider é obrigatório. Os adapters específicos de provider expõem intencionalmente detalhes de transporte enquanto mantêm o limite da aplicação neutro em relação ao provider.
