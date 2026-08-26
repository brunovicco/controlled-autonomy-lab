# Experiments

This document records live benchmark evidence for Controlled Autonomy Lab. It is intentionally narrower than a model leaderboard: the main purpose is to observe how the same incident-analysis task behaves as control moves from deterministic application code toward model-directed execution.

## Experimental question

> Given the same incident, evidence boundary, grounding evaluator, and autonomy pattern, what changes when control flow and provider/model behavior change?

The strongest comparisons are **within one provider**, where the incident and provider configuration stay fixed while the autonomy pattern changes. Cross-provider results are still useful, but they compare a bundle of model, transport, reasoning configuration, tokenization, infrastructure, and provider behavior rather than isolating the model alone.

## Shared setup

Both repeated experiments below used:

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

Across the two experiments, **60/60 pattern executions completed successfully**. Neither experiment recorded a rate-limit failure or provider error.

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

**The bounded agent reached `100%` specific grounding with one observed trajectory across five runs.** It averaged two model calls and five tool calls, with `10.38s` p50. For this model/provider configuration, delegating tool selection to the model did not produce the largest latency or a loss in the deterministic specific-grounding metric.

**Chaining and parallelization were the two weakest OpenAI patterns on specific grounding and also the two slowest.** Chaining reached `90.0%` grounding at `28.32s` p50; parallel reached `92.8%` at `24.79s` p50. This is evidence against assuming that more deterministic workflow structure automatically improves factual specificity.

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

**Evaluator-optimizer had the highest specific-grounding ratio in the Groq experiment** (`88.5%`) and no average causal overclaim, while requiring two model calls. This is a useful signal, but five repetitions on one incident are not enough to claim general superiority.

**Chaining was the weakest Groq pattern on specific grounding** (`67.4%`). It also averaged `1.2` causal overclaims and `2.0` proposed specifics per run. Together with the OpenAI result, chaining is the most consistent candidate for deeper investigation.

**The bounded agent showed substantially more trajectory variance than any other pattern.** Five runs produced four unique trajectories, with `5.2` model calls and `4.2` tool calls on average. This contrasts with the OpenAI agent, which produced one unique trajectory and averaged two model calls plus five tools.

This difference is important to the lab's control question: once the model owns tool selection and the next step, provider/model behavior can affect the execution path itself, not just the final wording.

## Cross-provider view

The table below is descriptive only. It does **not** isolate model quality because provider transport and reasoning configuration differ.

| Pattern | OpenAI grounding | Groq grounding | Difference | OpenAI p50 | Groq p50 | OpenAI/Groq latency ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 100.0% | 88.3% | +11.7 pp | 8.85s | 1.49s | 6.0x |
| Chaining | 90.0% | 67.4% | +22.6 pp | 28.32s | 4.26s | 6.6x |
| Routing | 100.0% | 87.8% | +12.2 pp | 8.61s | 2.12s | 4.1x |
| Parallel | 92.8% | 87.1% | +5.7 pp | 24.79s | 3.09s | 8.0x |
| Evaluator-optimizer | 100.0% | 88.5% | +11.5 pp | 9.38s | 2.11s | 4.4x |
| Agent | 100.0% | 82.6% | +17.4 pp | 10.38s | 4.00s | 2.6x |

Across these runs, the OpenAI configuration had the higher specific-grounding ratio in every pattern, while the Groq configuration had materially lower p50 latency in every pattern. That is a property of the **tested provider/model/configuration bundles**, not proof of an inherent model ranking.

Raw token counts should not be compared as equivalent units across providers. Tokenizers, reasoning accounting, API transports, and provider usage semantics differ. Within a provider, token counts are still useful for understanding the relative cost of the six control-flow patterns.

## Findings that currently have the strongest support

### 1. Chaining did not provide a grounding advantage

Chaining had the lowest specific-grounding ratio in both provider experiments: `90.0%` on OpenAI and `67.4%` on Groq. It also had the highest p50 latency on OpenAI and the highest p50 among the non-agent Groq workflows except for the agent itself.

A plausible mechanism is that sequential handoffs create multiple opportunities for unsupported inferences to be introduced and propagated, but the current experiment does **not** directly test that mechanism. It should be treated as a hypothesis for claim-level analysis, not as a demonstrated cause.

### 2. Evaluator-optimizer was consistently competitive

Evaluator-optimizer reached `100%` specific grounding on OpenAI and the highest Groq grounding (`88.5%`). Its latency remained close to routing in both providers relative to chaining and parallelization.

The result supports deeper study of evaluation/revision loops, but does not establish that an LLM evaluator is itself a proof of factual correctness. The project already separates evaluator-optimizer behavior from deterministic grounding evaluation for this reason.

### 3. Agent autonomy exposed provider/model-dependent trajectory behavior

The OpenAI agent produced one unique trajectory across five runs; the Groq agent produced four. OpenAI averaged `2.0` model calls and `5.0` tool calls, while Groq averaged `5.2` model calls and `4.2` tool calls.

This is the clearest evidence so far for the lab's central distinction:

> When deterministic application code owns the next step, execution topology is stable by construction. When the model owns the next step, model/provider behavior can change the execution trajectory itself.

This statement is limited to the observed runs and does not claim that one trajectory style is universally better.

### 4. Specific grounding and causal discipline are separate

The OpenAI routing pattern reached `100%` specific grounding while averaging `1.8` causal overclaims per run. This demonstrates why a single aggregate “hallucination score” would hide an important failure mode.

Grounding Evaluation v1 therefore keeps factual-specific support, proposed parameters, causal overclaim, and uncertainty preservation separate.

## Threats to validity

These results should be read with several limitations:

1. **One incident fixture.** All runs use `INC-001`; the findings may not generalize to different domains, ambiguity levels, tool sets, or evidence shapes.
2. **Small sample.** Five repetitions per pattern are enough to reveal useful variance signals but not enough for strong statistical claims.
3. **Provider bundle confounding.** OpenAI and Groq differ in model, transport, infrastructure, tokenization, max-output setting, and reasoning configuration.
4. **Different output caps.** OpenAI used `4000`; Groq used `900`. Those caps were selected after provider-specific smoke calibration and make the repeated experiments operationally stable, but they prevent an apples-to-apples token-budget claim.
5. **Different pacing.** OpenAI used a `2s` interval and Groq `30s`. The interval is only between independent pattern attempts and does not change the internal topology of a pattern, but it remains part of the experiment configuration.
6. **Grounding evaluator scope.** Grounding Evaluation v1 checks a deliberately narrow set of exact factual specifics, associations, proposal contexts, and causal language. It is not an NLI system or universal correctness metric.
7. **No persisted answer bodies.** Benchmark artifacts are metadata-only by design. Claim-level forensic analysis requires a separately approved observation mode or static captured fixtures; it cannot be reconstructed from `runs.jsonl` alone.
8. **Live-service variance.** Network and provider service conditions affect latency. The p50 values describe these runs, not guaranteed service-level behavior.
9. **No cost normalization yet.** Token counts are recorded, but provider-specific USD cost was not normalized in this experiment.

## What is not claimed

These experiments do not establish that:

- agents are better than workflows;
- workflows are safer than agents;
- GPT-5.6 Luna is universally better than GPT-OSS 20B;
- Groq is universally faster than OpenAI;
- more model calls necessarily reduce or increase hallucinations;
- `100%` specific grounding means a response is fully correct;
- an LLM evaluator's acceptance proves groundedness.

## Next experiments

The most useful next steps are:

1. add Anthropic Claude Sonnet 5 as a third provider experiment once API credits are available;
2. add a claim-level evaluation phase that classifies `SUPPORTED_FACT`, `SUPPORTED_INFERENCE`, `PROPOSED_ACTION`, and `UNSUPPORTED_CLAIM`;
3. add static observed-run fixtures so evaluator development does not depend on live provider quota;
4. compare evaluator-optimizer acceptance with deterministic/semantic grounding findings;
5. analyze relational errors separately from bag-of-values factual errors;
6. add provider-aware cost normalization in USD while preserving raw provider token metadata;
7. repeat the experiment on additional incident fixtures before making broader architecture claims.

## Reproducibility note

The repeated OpenAI and Groq experiments documented here were both executed from Git commit:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

Earlier smoke and calibration runs used different transports, output budgets, pacing, or pre-hardening commits. They remain useful debugging evidence, but they are intentionally excluded from this repeated-experiment comparison.
