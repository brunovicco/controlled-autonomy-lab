# Frozen Three-Provider Benchmark

## Purpose

This document consolidates the repeated architecture benchmark for three provider/model bundles on the same frozen implementation.

It is not a model leaderboard. The experiment compares **provider/model/configuration bundles** while holding the incident, six architecture patterns, benchmark runner, deterministic Grounding Evaluation v1, retry policy, and persistence boundary fixed.

## Frozen setup

All three repeated experiments use:

- incident: `INC-001`;
- Git commit: `1f8f8b892b033957c73e6260f12edb75e321462c`;
- repetitions: `5` per pattern;
- six patterns per provider;
- `30` pattern executions per provider;
- `90` executions total;
- deterministic rotating pattern order;
- no hidden retries;
- metadata-only benchmark artifacts;
- deterministic Grounding Evaluation v1.

All **90/90 executions completed successfully**. No repeated experiment recorded a rate-limit failure or provider error.

The six patterns are:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

## Provider bundles

| Bundle | Transport | Max output tokens | Timeout | Reasoning | Attempt interval |
| --- | --- | ---: | ---: | --- | ---: |
| OpenAI `gpt-5.6-luna` | native Responses API | 4000 | 60s | provider-defined/default | 2s |
| Groq `openai/gpt-oss-20b` | OpenAI-compatible Chat Completions | 900 | 30s | medium | 30s |
| Anthropic `claude-sonnet-5` | Anthropic Messages API | 4000 | 60s | provider-defined/default | 10s |

The different transports, token budgets, provider infrastructure, tokenization, and reasoning settings are part of the tested bundles. Cross-provider results therefore describe the bundles, not isolated model quality.

## Specific grounding by pattern

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | 95.3% |
| Chaining | 90.0% | 67.4% | 82.1% |
| Routing | 100.0% | 87.8% | 84.6% |
| Parallel | 92.8% | 87.1% | 94.8% |
| Evaluator-optimizer | 100.0% | 88.5% | 96.7% |
| Agent | 100.0% | 82.6% | 93.6% |

Mean of the six per-pattern grounding aggregates, shown only as a compact descriptive summary:

- OpenAI: `97.1%`;
- Anthropic: `91.2%`;
- Groq: `83.6%`.

This mean is not a statistical estimate of general model accuracy. It averages six pattern-level summaries from one incident fixture.

## p50 latency by pattern

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 8.85s | 1.49s | 15.71s |
| Chaining | 28.32s | 4.26s | 39.31s |
| Routing | 8.61s | 2.12s | 14.40s |
| Parallel | 24.79s | 3.09s | 40.37s |
| Evaluator-optimizer | 9.38s | 2.11s | 16.21s |
| Agent | 10.38s | 4.00s | 16.88s |

Groq had the lowest p50 latency in every pattern in this sample. Anthropic had the highest p50 latency in five of six patterns; parallelization was slightly slower than chaining on Anthropic.

These values describe live provider conditions during the runs and are not service-level guarantees.

## Token usage by pattern

| Pattern | OpenAI | Groq | Anthropic |
| --- | ---: | ---: | ---: |
| Augmented | 877 | 1,250 | 1,786 |
| Chaining | 3,838 | 4,087 | 6,027 |
| Routing | 910 | 1,769 | 1,827 |
| Parallel | 5,530 | 5,890 | 9,284 |
| Evaluator-optimizer | 1,576 | 2,248 | 3,053 |
| Agent | 1,662 | 4,342 | 4,354 |

Raw token counts are useful **within a provider** for comparing patterns. They are not equivalent accounting units across providers because tokenizers, reasoning accounting, and API semantics differ.

## Unsupported, proposed, and causal findings

### OpenAI

| Pattern | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 0.0 | 0.0 | 0.6 |
| Chaining | 0.2 | 0.0 | 0.4 |
| Routing | 0.0 | 0.0 | 1.8 |
| Parallel | 0.8 | 0.2 | 0.0 |
| Evaluator-optimizer | 0.0 | 0.0 | 0.2 |
| Agent | 0.0 | 0.0 | 0.2 |

### Groq

| Pattern | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 1.6 | 0.4 | 0.6 |
| Chaining | 1.6 | 2.0 | 1.2 |
| Routing | 1.8 | 0.0 | 0.6 |
| Parallel | 1.4 | 0.2 | 0.2 |
| Evaluator-optimizer | 1.4 | 0.0 | 0.0 |
| Agent | 2.4 | 1.4 | 0.4 |

### Anthropic

| Pattern | Unsupported | Proposed | Causality |
| --- | ---: | ---: | ---: |
| Augmented | 0.6 | 0.0 | 0.6 |
| Chaining | 1.2 | 0.2 | 1.2 |
| Routing | 2.0 | 0.0 | 1.8 |
| Parallel | 0.6 | 0.0 | 1.4 |
| Evaluator-optimizer | 0.4 | 0.4 | 0.8 |
| Agent | 0.8 | 0.6 | 1.4 |

Specific grounding and causal discipline remain separate dimensions. For example, OpenAI routing had `100%` specific grounding while averaging `1.8` causality findings; Anthropic routing had `84.6%` grounding and the same `1.8` causality average.

## Strongest findings across all three bundles

### 1. Chaining was the most consistently weak grounding pattern

Chaining had the lowest specific-grounding ratio in all three provider experiments:

- OpenAI: `90.0%`;
- Groq: `67.4%`;
- Anthropic: `82.1%`.

It was also among the highest-latency patterns in every provider. This is evidence that sequential decomposition did not create a grounding advantage for this incident.

A plausible mechanism is unsupported inference propagation across sequential handoffs, but the repeated benchmark does not directly prove that mechanism.

### 2. Evaluator-optimizer was consistently competitive

Evaluator-optimizer was tied for the highest grounding on OpenAI (`100%`) and was the highest-grounding pattern on both Groq (`88.5%`) and Anthropic (`96.7%`).

It also remained materially cheaper and faster than chaining and parallelization within OpenAI and Anthropic. The result supports further study of evaluator/revision loops, but an LLM evaluator is not itself evidence of correctness.

### 3. Agent trajectory behavior depended strongly on the provider/model bundle

| Bundle | Model calls | Tool calls | Unique trajectories |
| --- | ---: | ---: | ---: |
| OpenAI | 2.0 | 5.0 | 1 |
| Groq | 5.2 | 4.2 | 4 |
| Anthropic | 2.0 | 5.0 | 1 |

OpenAI and Anthropic produced the same coarse agent topology across five runs: two model calls, all five read-only tools, and one observed trajectory. Groq produced four trajectories, more model calls, and fewer tool calls on average.

This strengthens the lab's central control-boundary observation:

> Once the model owns tool selection and the next step, provider/model behavior can alter the execution trajectory itself.

It does **not** establish that one trajectory style is universally better.

### 4. More workflow structure did not monotonically improve grounding

Parallelization and chaining both used more model calls than augmented or routing, but neither showed a consistent grounding advantage. The relationship between model-call count and grounding is therefore not monotonic in these runs.

### 5. Grounding and causal discipline must remain separate metrics

High specific grounding did not guarantee low causal overclaim. This is visible especially in routing and in some Anthropic patterns. A single aggregate hallucination score would hide this distinction.

## Within-provider observations

### OpenAI

- lowest p50: routing (`8.61s`);
- highest grounding: augmented, routing, evaluator-optimizer, and agent (`100%`);
- weakest grounding: chaining (`90.0%`);
- agent topology: stable, one trajectory.

### Groq

- lowest p50: augmented (`1.49s`);
- highest grounding: evaluator-optimizer (`88.5%`);
- weakest grounding: chaining (`67.4%`);
- agent topology: highest observed trajectory variance (`4`).

### Anthropic

- lowest p50: routing (`14.40s`);
- highest grounding: evaluator-optimizer (`96.7%`);
- weakest grounding: chaining (`82.1%`);
- agent topology: stable, one trajectory;
- parallelization consumed the most tokens (`9,284`) and had the highest p50 (`40.37s`).

## Threats to validity

1. **One incident fixture.** All 90 runs use `INC-001`.
2. **Small repeated sample.** `n=5` per pattern/provider exposes variance but does not support strong statistical claims.
3. **Provider-bundle confounding.** Model, transport, infrastructure, tokenization, output caps, and reasoning settings differ.
4. **Different output caps.** OpenAI and Anthropic used `4000`; Groq used `900` after provider-specific calibration.
5. **Different pacing.** Attempt intervals were 2s, 30s, and 10s respectively.
6. **Grounding-v1 scope.** The evaluator is bounded and lexical/structural, not universal semantic correctness or NLI.
7. **Metadata-only persistence.** Raw answer bodies are deliberately excluded from repeated benchmark artifacts.
8. **Live-service variance.** Latency includes real provider/network conditions.
9. **No cost normalization.** Raw provider token counts are not yet translated into provider-aware USD cost.

## What is not claimed

The 90-run benchmark does not establish that:

- one model is universally better than another;
- agents are better than workflows;
- workflows are safer than agents;
- Groq is universally faster;
- evaluator-optimizer guarantees correctness;
- chaining is universally bad;
- `100%` specific grounding means a fully correct response;
- token counts are directly comparable across providers.

## Next experiments

The next high-value steps are:

1. repeat the six patterns across additional incident fixtures;
2. strengthen relational/contextual deterministic evaluation using the human-labelled claim matrix;
3. add provider-aware cost normalization while preserving raw token metadata;
4. compare static claim-evaluator behavior across independent judges;
5. revisit sample size only after incident diversity improves.

Increasing repetitions on `INC-001` alone is lower-value than adding new incident types at this stage.
