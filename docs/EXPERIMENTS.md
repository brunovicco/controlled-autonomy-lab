# Experiments

This document records live benchmark evidence for Controlled Autonomy Lab. It is intentionally narrower than a model leaderboard: the main purpose is to observe how the same incident-analysis task behaves as control moves from deterministic application code toward model-directed execution.

For the compact three-provider comparison, see [`FROZEN_THREE_PROVIDER_BENCHMARK.md`](FROZEN_THREE_PROVIDER_BENCHMARK.md).

## Experimental question

> Given the same incident, evidence boundary, grounding evaluator, and autonomy pattern, what changes when control flow and provider/model behavior change?

The strongest comparisons are **within one provider**, where the incident and provider configuration stay fixed while the autonomy pattern changes. Cross-provider results are still useful, but they compare a bundle of model, transport, reasoning configuration, tokenization, infrastructure, and provider behavior rather than isolating the model alone.

## Shared setup

All three repeated experiments used:

- incident: `INC-001`;
- Git commit: `1f8f8b892b033957c73e6260f12edb75e321462c`;
- repetitions: `5` per pattern;
- six patterns per provider;
- deterministic rotating pattern order across cycles;
- no hidden retries;
- deterministic Grounding Evaluation v1;
- metadata-only benchmark artifacts;
- successful-run aggregates for execution and grounding metrics;
- all attempted runs for reliability rates.

Across the three experiments, **90/90 pattern executions completed successfully**. No repeated experiment recorded a rate-limit failure or provider error.

The six patterns were:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

## Experiment 1 — OpenAI GPT-5.6 Luna

Configuration:

- provider: `openai`;
- model: `gpt-5.6-luna`;
- transport: native OpenAI Responses API;
- max output tokens: `4000`;
- timeout: `60s`;
- reasoning effort: provider-defined/default;
- interval between benchmark attempts: `2s`;
- status: complete (`30/30`).

| Pattern | Calls | Tools | Avg tokens | p50 latency | Unsupported | Proposed | Causality | Grounding | Trajectories |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 877 | 8,847.6 ms | 0.0 | 0.0 | 0.6 | 100.0% | 1 |
| Chaining | 3.0 | 0.0 | 3,838 | 28,317.4 ms | 0.2 | 0.0 | 0.4 | 90.0% | 1 |
| Routing | 2.0 | 0.0 | 910 | 8,611.5 ms | 0.0 | 0.0 | 1.8 | 100.0% | 1 |
| Parallel | 4.0 | 0.0 | 5,530 | 24,791.8 ms | 0.8 | 0.2 | 0.0 | 92.8% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 1,576 | 9,382.9 ms | 0.0 | 0.0 | 0.2 | 100.0% | 1 |
| Agent | 2.0 | 5.0 | 1,662 | 10,376.4 ms | 0.0 | 0.0 | 0.2 | 100.0% | 1 |

### OpenAI observations

**Routing was the lowest-latency OpenAI pattern** in this sample (`8.61s` p50), narrowly ahead of augmented (`8.85s`). Both had a `100%` specific-grounding ratio.

**Evaluator-optimizer also reached `100%` specific grounding** with two model calls and `9.38s` p50. In this experiment the extra evaluation step did not create the highest latency or token use.

**The bounded agent reached `100%` specific grounding with one observed trajectory across five runs.** It averaged two model calls and five tool calls, with `10.38s` p50.

**Chaining and parallelization were the two weakest OpenAI patterns on specific grounding and also the two slowest.** Chaining reached `90.0%` grounding at `28.32s` p50; parallel reached `92.8%` at `24.79s` p50.

A separate caution is visible in **routing**: it had `100%` specific grounding while averaging `1.8` causality overclaims per run. Grounding Evaluation v1 deliberately treats exact factual support and causal overclaim as different dimensions. Therefore, `100%` specific grounding must not be read as “fully correct answer.”

## Experiment 2 — Groq GPT-OSS 20B

Configuration:

- provider: `groq`;
- model: `openai/gpt-oss-20b`;
- transport: OpenAI-compatible Chat Completions;
- max output tokens: `900`;
- timeout: `30s`;
- reasoning effort: `medium`;
- interval between benchmark attempts: `30s`;
- status: complete (`30/30`).

| Pattern | Calls | Tools | Avg tokens | p50 latency | Unsupported | Proposed | Causality | Grounding | Trajectories |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 1,250 | 1,485.6 ms | 1.6 | 0.4 | 0.6 | 88.3% | 1 |
| Chaining | 3.0 | 0.0 | 4,087 | 4,263.2 ms | 1.6 | 2.0 | 1.2 | 67.4% | 1 |
| Routing | 2.0 | 0.0 | 1,769 | 2,116.3 ms | 1.8 | 0.0 | 0.6 | 87.8% | 1 |
| Parallel | 4.0 | 0.0 | 5,890 | 3,093.8 ms | 1.4 | 0.2 | 0.2 | 87.1% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 2,248 | 2,111.4 ms | 1.4 | 0.0 | 0.0 | 88.5% | 1 |
| Agent | 5.2 | 4.2 | 4,342 | 4,000.4 ms | 2.4 | 1.4 | 0.4 | 82.6% | 4 |

### Groq observations

**Augmented was the lowest-latency Groq pattern** (`1.49s` p50). Evaluator-optimizer and routing followed at roughly `2.11s`.

**Evaluator-optimizer had the highest specific-grounding ratio in the Groq experiment** (`88.5%`) and no average causal overclaim, while requiring two model calls.

**Chaining was the weakest Groq pattern on specific grounding** (`67.4%`). It also averaged `1.2` causal overclaims and `2.0` proposed specifics per run.

**The bounded agent showed substantially more trajectory variance than any other pattern.** Five runs produced four unique trajectories, with `5.2` model calls and `4.2` tool calls on average.

## Experiment 3 — Anthropic Claude Sonnet 5

Configuration:

- provider: `anthropic`;
- model: `claude-sonnet-5`;
- transport: Anthropic Messages API;
- max output tokens: `4000`;
- timeout: `60s`;
- reasoning effort: provider-defined/default;
- interval between benchmark attempts: `10s`;
- status: complete (`30/30`).

| Pattern | Calls | Tools | Avg tokens | p50 latency | Unsupported | Proposed | Causality | Grounding | Trajectories |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 1.0 | 0.0 | 1,786 | 15,713.2 ms | 0.6 | 0.0 | 0.6 | 95.3% | 1 |
| Chaining | 3.0 | 0.0 | 6,027 | 39,311.0 ms | 1.2 | 0.2 | 1.2 | 82.1% | 1 |
| Routing | 2.0 | 0.0 | 1,827 | 14,397.9 ms | 2.0 | 0.0 | 1.8 | 84.6% | 1 |
| Parallel | 4.0 | 0.0 | 9,284 | 40,371.3 ms | 0.6 | 0.0 | 1.4 | 94.8% | 1 |
| Evaluator-optimizer | 2.0 | 0.0 | 3,053 | 16,210.0 ms | 0.4 | 0.4 | 0.8 | 96.7% | 1 |
| Agent | 2.0 | 5.0 | 4,354 | 16,876.2 ms | 0.8 | 0.6 | 1.4 | 93.6% | 1 |

### Anthropic observations

**Routing was the lowest-latency Anthropic pattern** (`14.40s` p50), followed by augmented (`15.71s`) and evaluator-optimizer (`16.21s`).

**Evaluator-optimizer had the highest Anthropic specific-grounding ratio** (`96.7%`). It was also materially cheaper and faster than chaining and parallelization within the Anthropic bundle.

**Chaining again had the lowest specific-grounding ratio** (`82.1%`). Parallelization had the highest p50 (`40.37s`) and highest average token usage (`9,284`).

**The bounded Anthropic agent showed the same coarse topology as OpenAI**: two model calls, five tool calls, and one observed trajectory across five runs.

The Anthropic CSV reported an uncertainty-preservation rate of `1.0` for every pattern in this sample. This is descriptive evidence for these runs, not a general provider guarantee.

## Cross-provider view

The table below is descriptive only. It does **not** isolate model quality because provider transport, reasoning configuration, output budget, tokenization, infrastructure, and pacing differ.

### Specific grounding

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | 95.3% |
| Chaining | 90.0% | 67.4% | 82.1% |
| Routing | 100.0% | 87.8% | 84.6% |
| Parallel | 92.8% | 87.1% | 94.8% |
| Evaluator-optimizer | 100.0% | 88.5% | 96.7% |
| Agent | 100.0% | 82.6% | 93.6% |

### p50 latency

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 8.85s | 1.49s | 15.71s |
| Chaining | 28.32s | 4.26s | 39.31s |
| Routing | 8.61s | 2.12s | 14.40s |
| Parallel | 24.79s | 3.09s | 40.37s |
| Evaluator-optimizer | 9.38s | 2.11s | 16.21s |
| Agent | 10.38s | 4.00s | 16.88s |

Across these runs, the OpenAI bundle had the higher specific-grounding ratio in five of six patterns; Anthropic was higher on parallelization. Groq had the lowest p50 latency in all six patterns. These are properties of the **tested provider/model/configuration bundles**, not proof of an inherent model ranking.

Raw token counts should not be compared as equivalent units across providers. Within a provider, token counts are still useful for understanding the relative cost of the six control-flow patterns.

## Findings that currently have the strongest support

### 1. Chaining did not provide a grounding advantage

Chaining had the lowest specific-grounding ratio in all three repeated experiments: `90.0%` on OpenAI, `67.4%` on Groq, and `82.1%` on Anthropic. It was also among the highest-latency patterns in every provider.

A plausible mechanism is that sequential handoffs create multiple opportunities for unsupported inferences to be introduced and propagated, but the current experiment does **not** directly test that mechanism.

### 2. Evaluator-optimizer was consistently competitive

Evaluator-optimizer reached `100%` specific grounding on OpenAI and the highest grounding in both the Groq (`88.5%`) and Anthropic (`96.7%`) experiments.

The result supports deeper study of evaluation/revision loops, but does not establish that an LLM evaluator is itself proof of factual correctness.

### 3. Agent autonomy exposed provider/model-dependent trajectory behavior

| Bundle | Model calls | Tool calls | Unique trajectories |
| --- | ---: | ---: | ---: |
| OpenAI | 2.0 | 5.0 | 1 |
| Groq | 5.2 | 4.2 | 4 |
| Anthropic | 2.0 | 5.0 | 1 |

OpenAI and Anthropic produced the same coarse agent topology across five runs. Groq produced four unique trajectories, more model calls, and fewer tool calls on average.

This is the clearest evidence so far for the lab's central distinction:

> When deterministic application code owns the next step, execution topology is stable by construction. When the model owns the next step, model/provider behavior can change the execution trajectory itself.

This statement is limited to the observed runs and does not claim that one trajectory style is universally better.

### 4. Specific grounding and causal discipline are separate

High specific grounding did not guarantee low causal overclaim. OpenAI routing reached `100%` specific grounding while averaging `1.8` causal overclaims per run; Anthropic routing averaged the same `1.8` causality findings at `84.6%` specific grounding.

Grounding Evaluation v1 therefore keeps factual-specific support, proposed parameters, causal overclaim, and uncertainty preservation separate.

### 5. More model calls did not monotonically improve grounding

Chaining and parallelization use more model calls than augmented or routing, but neither demonstrated a consistent grounding advantage. In this experiment, workflow complexity and factual grounding were not monotonic.

## Threats to validity

These results should be read with several limitations:

1. **One incident fixture.** All runs use `INC-001`; the findings may not generalize to different domains, ambiguity levels, tool sets, or evidence shapes.
2. **Small sample.** Five repetitions per pattern/provider reveal useful variance signals but are not enough for strong statistical claims.
3. **Provider bundle confounding.** OpenAI, Groq, and Anthropic differ in model, transport, infrastructure, tokenization, max-output setting, reasoning configuration, and pacing.
4. **Different output caps.** OpenAI and Anthropic used `4000`; Groq used `900`. The caps were selected after provider-specific smoke calibration and prevent an apples-to-apples token-budget claim.
5. **Different pacing.** Attempt intervals were OpenAI `2s`, Groq `30s`, and Anthropic `10s`. These intervals are between independent benchmark attempts only and do not serialize calls inside a pattern.
6. **Grounding evaluator scope.** Grounding Evaluation v1 is deliberately bounded and lexical/structural. It is not an NLI system or universal correctness metric.
7. **No persisted answer bodies.** Benchmark artifacts are metadata-only by design. Claim-level forensic analysis requires separately approved observation or static fixtures.
8. **Live-service variance.** Network and provider service conditions affect latency. The p50 values describe these runs, not guaranteed service-level behavior.
9. **No cost normalization yet.** Token counts are recorded, but provider-aware USD cost has not been normalized.

## What is not claimed

These experiments do not establish that:

- agents are better than workflows;
- workflows are safer than agents;
- one provider/model is universally better than another;
- Groq is universally faster than OpenAI or Anthropic;
- evaluator-optimizer guarantees correctness;
- chaining is universally bad;
- more model calls necessarily reduce or increase hallucinations;
- `100%` specific grounding means a response is fully correct;
- an LLM evaluator's acceptance proves groundedness;
- raw token counts are directly comparable across providers.

## Next experiments

The most useful next steps are now:

1. repeat the six patterns across additional incident fixtures before increasing repetitions on `INC-001`;
2. strengthen relational/contextual deterministic evaluation using the human-labelled claim matrix;
3. compare static claim-evaluator behavior across independent semantic judges;
4. add provider-aware cost normalization in USD while preserving raw provider token metadata;
5. compare evaluator-optimizer acceptance with deterministic and semantic claim-level findings.

## Reproducibility note

The repeated OpenAI, Groq, and Anthropic experiments documented here were all executed from Git commit:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

The Anthropic frozen run produced exactly `30` metadata rows in `runs.jsonl`, matching five repetitions across six patterns.

Earlier smoke and calibration runs used different transports, output budgets, pacing, evaluators, or later commits. They remain useful debugging/calibration evidence, but they are intentionally excluded from this frozen repeated-experiment comparison.
