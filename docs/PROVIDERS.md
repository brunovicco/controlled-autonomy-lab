# LLM providers

Controlled Autonomy Lab keeps provider transport outside the application patterns. Switching provider should not change workflow topology, agent authority or evidence rules.

## Selection

Set `LLM_PROVIDER` to one of:

```text
anthropic
openai
groq
openrouter
custom
```

Optional shared limits:

```bash
export LLM_MAX_TOKENS=1200
export LLM_TIMEOUT_SECONDS=30
```

## OpenRouter — recommended free starting point

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL=openrouter/free
```

`openrouter/free` is a router over free models rather than one pinned model. This makes the lab accessible without paid inference, but it also means the underlying model may vary. That is useful to remember when comparing latency, quality or trajectory variance.

OpenRouter documents that the free router filters available free models according to request features, including tool calling when required. Free availability and limits are provider-controlled and may change.

Official docs:
- https://openrouter.ai/docs/guides/routing/routers/free-models-router
- https://openrouter.ai/pricing

## Groq — Free Plan alternative

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY="..."
export GROQ_MODEL=openai/gpt-oss-20b
```

The preset uses Groq's OpenAI-compatible base URL. Groq publishes separate Free Plan rate limits by model. The default model can be overridden without changing code.

Official docs:
- https://console.groq.com/docs/openai
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/tool-use/overview

## Anthropic

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY="..."
export CLAUDE_MODEL=claude-sonnet-5
```

Anthropic uses its native Messages API adapter rather than the OpenAI-compatible adapter.

Official docs:
- https://platform.claude.com/docs/en/api/messages/create
- https://platform.claude.com/docs/en/about-claude/models/overview

## OpenAI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_MODEL=gpt-5.6-luna
```

The preset uses Chat Completions and function calling. Override `OPENAI_MODEL` if you want to compare another model that supports the required capabilities.

Official docs:
- https://developers.openai.com/api/docs/models
- https://developers.openai.com/api/reference/resources/chat

## Custom OpenAI-compatible endpoint

```bash
export LLM_PROVIDER=custom
export OPENAI_COMPAT_API_KEY="..."
export OPENAI_COMPAT_BASE_URL="https://provider.example/v1"
export OPENAI_COMPAT_MODEL="provider-model"
```

The base URL must use HTTPS and cannot contain embedded credentials, a query or fragment. The adapter appends `/chat/completions`.

Text-only patterns require compatible Chat Completions semantics. The agent additionally requires OpenAI-style function/tool calling. A provider that accepts basic chat but not tool calls can still be used with `augmented`, `chaining`, `routing`, `parallel` and `evaluator-optimizer`, but not necessarily with `agent`.

## Fair comparisons

Provider switching introduces more than a model-name change. For useful comparisons:

1. Pin a concrete model instead of a router when reproducibility matters.
2. Keep the same incident fixture and pattern configuration.
3. Keep `LLM_MAX_TOKENS` and budgets constant.
4. Repeat stochastic/model-controlled patterns more than once.
5. Record metadata-only traces to compare model calls, tool calls, token use, latency and trajectory.
6. Do not interpret differences in provider token accounting as perfectly equivalent billing units.

No provider SDK is required. Both adapters intentionally expose the transport details so the control-flow comparison remains visible.
