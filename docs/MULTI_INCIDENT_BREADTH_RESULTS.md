# Multi-Incident Breadth Benchmark Results

## Purpose

This document reports the main multi-incident breadth generation for the Controlled Autonomy Lab.

The experiment extends the earlier repeated three-provider benchmark by changing the evidence posture across four canonical incidents while keeping the six architecture patterns fixed.

The objective is not to produce a model leaderboard.

It asks a narrower architecture question:

> Do observed properties of augmented generation, chaining, routing, parallelization, evaluator-optimizer loops, and bounded tool-using agents persist when the evidence changes from correlation, to confirmed causes, to an inconclusive case requiring abstention?

The breadth generation is intentionally descriptive:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

There is one run per cell. The results therefore support architecture-oriented observations and hypotheses, not statistical significance claims.

---

## Frozen experimental boundary

The main breadth generation was frozen at:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

All three provider bundles ran against that exact implementation.

The frozen commit includes the benchmark behavior that preserves bounded-agent exhaustion as benchmark evidence rather than allowing it to escape as an unclassified runner exception.

Historical calibration generations are not mixed into the results reported here.

Excluded generations include:

- the earlier OpenAI breadth calibration on `14863271f5054756f59227175847e9521b0621c3`;
- the Groq pre-fix generation that exposed the bounded-agent runner failure;
- the post-fix Groq calibration accidentally executed with `max_tokens=1200`.

Only the explicitly frozen main generation is analyzed below.

---

## Canonical incidents

| Incident | Evidence posture |
| --- | --- |
| `INC-001` | correlation without a proven current cause |
| `INC-002` | deployment cause explicitly confirmed |
| `INC-003` | dependency cause explicitly confirmed |
| `INC-004` | inconclusive evidence; abstention expected |

These incidents intentionally vary the amount of causal authority supported by the evidence.

That distinction matters because specific factual grounding and causal correctness are evaluated separately.

---

## Architecture patterns

The same six patterns were executed for every incident/provider bundle:

1. augmented LLM;
2. prompt chaining;
3. routing;
4. parallelization;
5. evaluator-optimizer;
6. bounded tool-using agent.

The agent remains intentionally constrained.

It uses read-only tools, an explicit allowlist, bounded steps, and bounded tool calls. It cannot restart services, write configuration, execute shell commands, perform rollback, or mutate production state.

The benchmark therefore evaluates **bounded autonomy**, not unrestricted autonomous operation.

---

## Provider bundles

| Bundle | Model | Transport | Max output tokens | Timeout | Reasoning | Attempt interval |
| --- | --- | --- | ---: | ---: | --- | ---: |
| OpenAI | `gpt-5.6-luna` | native Responses API | 4000 | 60s | provider-defined/default | 2s |
| Groq | `openai/gpt-oss-20b` | OpenAI-compatible API | 900 | 30s | medium | 30s |
| Anthropic | `claude-sonnet-5` | Anthropic Messages API | 4000 | 60s | provider-defined/default | 10s |

Transport, provider infrastructure, tokenization, output limits, reasoning configuration, and live-service conditions are part of each tested bundle.

Cross-provider comparisons therefore describe **provider/model/API/config bundles**, not isolated model quality.

---

# Availability before quality

Availability is analyzed separately from answer quality.

A rate-limited or provider-error cell is not assigned zero grounding, zero causal correctness, or any other imputed quality value.

## Main generation

| Provider | Attempts | Successful | Rate limited | Provider error | Completion |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 0 | 0 | 100.0% |
| Groq | 24 | 12 | 12 | 0 | 50.0% |
| Anthropic | 24 | 23 | 0 | 1 | 95.8% |
| **Total** | **72** | **59** | **12** | **1** | **81.9%** |

The Groq failures were not distributed by architecture pattern.

Instead:

- `INC-001`: 6/6 successful;
- `INC-002`: 6/6 successful;
- `INC-003`: 6/6 rate-limited;
- `INC-004`: 6/6 rate-limited.

Every pattern therefore has exactly two observed and two rate-limited Groq cells.

This is a provider-level availability confound rather than evidence that all six architecture patterns independently failed at the same rate.

Anthropic had one provider error:

```text
INC-003 / chaining
Anthropic request failed
```

The cell is preserved as provider availability evidence and is not rerun or converted into a quality observation.

---

# Architecture-level results

Quality, cost, latency, and trajectory metrics below use only cells where:

```text
status = ok
```

| Pattern | Observed | Mean grounding | Causal overclaims | Zero-overclaim cells | Mean model calls | Mean tool calls | Mean tokens | p50 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 10/12 | 97.8% | 3 | 70.0% | 1.0 | 0.0 | 1,264 | 7.69s |
| Chaining | 9/12 | 74.4% | 5 | 66.7% | 3.0 | 0.0 | 4,769 | 26.34s |
| Routing | 10/12 | 92.8% | 2 | 80.0% | 2.0 | 0.0 | 1,560 | 7.15s |
| Parallel | 10/12 | 94.9% | 7 | 60.0% | 4.0 | 0.0 | 7,141 | 21.81s |
| Evaluator-optimizer | 10/12 | 97.6% | 4 | 70.0% | 2.4 | 0.0 | 3,427 | 9.13s |
| Agent | 10/12 | 95.4% | **0** | **100.0%** | 2.5 | 4.7 | 3,158 | 7.03s |

These values expose several different trade-offs. No single metric is sufficient to rank the architectures.

---

# Finding 1 — Bounded agency showed the strongest observed causal restraint

The bounded tool-using agent was the only architecture pattern with:

```text
0 detected causal overclaims
```

across every successful breadth cell.

Observed coverage was:

- OpenAI: 4/4 incidents;
- Groq: 2/4 incidents, with the remaining two blocked by provider rate limits;
- Anthropic: 4/4 incidents.

That gives ten observable agent cells with zero causal overclaims.

This includes the two incidents where causal restraint matters most:

- `INC-001`, where correlation exists but a current cause is not proven;
- `INC-004`, where evidence remains inconclusive and abstention is expected.

The signal is not simply a consequence of maximizing the grounding score.

Agent mean specific grounding was `95.4%`, while augmented and evaluator-optimizer both exceeded `97%`.

The observed distinction is therefore:

> high grounding combined with stronger causal restraint.

This result supports further study of bounded tool-using agency as a mechanism for evidence acquisition under explicit control limits.

It does **not** establish that agents are universally safer, more accurate, or better than workflows.

---

# Finding 2 — The agent signal appeared across different provider behaviors

The coarse agent topology differed materially across provider bundles.

## OpenAI

All four incidents used:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> search_runbook
-> get_previous_incidents
-> final-answer
```

Each run used:

```text
2 model calls
5 tool calls
```

## Anthropic

Anthropic produced the same coarse trajectory as OpenAI across all four incidents:

```text
2 model calls
5 tool calls
```

## Groq

The two observable incidents were different.

`INC-001`:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> get_previous_incidents
-> final-answer
```

with:

```text
5 model calls
4 tool calls
```

`INC-002`:

```text
get_service_metrics
-> get_recent_deployments
-> get_dependencies
-> final-answer
```

with:

```text
4 model calls
3 tool calls
```

Despite this execution-topology variation, none of the ten successful agent cells produced a detected causal overclaim.

The result strengthens a central Controlled Autonomy Lab observation:

> When the model owns tool selection and the next step, changing the provider/model bundle can alter execution topology itself.

The breadth generation adds an additional observation:

> Different bounded trajectories can still exhibit similar causal restraint within the observed cases.

Neither statement implies that one provider trajectory style is universally preferable.

---

# Finding 3 — Chaining had the weakest overall trade-off

Prompt chaining produced:

- the lowest mean specific grounding: `74.4%`;
- 5 causal overclaims;
- approximately `4,769` mean tokens;
- three model calls per successful cell;
- the highest architecture-level p50 latency: `26.34s`.

The most important result occurred in `INC-004`.

That incident explicitly requires restraint because the evidence remains inconclusive.

Across the two observable chaining cells:

```text
4 causal overclaims
0% zero-overclaim rate
75.7% mean grounding
```

This makes chaining particularly weak for the abstention-oriented incident in this generation.

The benchmark does not directly prove why.

A plausible mechanism is inference propagation across sequential stages, but that remains a hypothesis rather than an experimentally established causal mechanism.

The supported conclusion is narrower:

> In this breadth generation, additional sequential decomposition did not translate into better grounding or better causal discipline.

---

# Finding 4 — Parallelization increased coverage cost without guaranteeing causal discipline

Parallelization maintained relatively high mean specific grounding:

```text
94.9%
```

but produced the largest number of detected causal overclaims:

```text
7
```

It was also the most token-intensive pattern:

```text
7,141 mean tokens
```

with:

```text
4 model calls
21.81s p50 latency
```

The result is particularly important because the earlier calibration evidence had made parallelization look comparatively causally disciplined.

The multi-incident breadth generation did not preserve that signal.

This illustrates why the first calibration should not have been treated as a final architecture conclusion.

A fan-out/fan-in topology can improve evidence coverage while still leaving the synthesis stage responsible for reconciling conflicting or incomplete evidence.

The observed results therefore support keeping two distinct questions:

1. Did the workflow retrieve and mention supported facts?
2. Did the final synthesis claim more causal authority than those facts justify?

Parallelization performed well on the first dimension but less consistently on the second.

---

# Finding 5 — Grounding and causal correctness are distinct dimensions

Several cells had perfect specific grounding while still producing causal overclaims.

Examples include:

- OpenAI parallel on `INC-001`: `100%` grounding with 3 overclaims;
- Anthropic augmented on `INC-001`: `100%` grounding with 1 overclaim;
- Anthropic evaluator-optimizer on `INC-001`: `100%` grounding with 2 overclaims;
- Anthropic augmented on `INC-003`: `100%` grounding with 1 overclaim;
- OpenAI evaluator-optimizer on `INC-003`: `100%` grounding with 1 overclaim;
- OpenAI evaluator-optimizer on `INC-004`: `100%` grounding with 1 overclaim;
- Anthropic parallel on `INC-004`: `100%` grounding with 1 overclaim.

A response can therefore accurately reference available evidence and still infer more causal certainty than the evidence supports.

This validates the decision to evaluate:

```text
specific grounding
```

and:

```text
causal authority
```

as separate dimensions.

A single aggregate hallucination score would hide this difference.

---

# Finding 6 — Ambiguous and inconclusive incidents concentrated causal failures

Across the successful breadth cells, the evaluator detected:

```text
21 total causal overclaims
```

Their distribution by incident was:

| Incident | Causal overclaims |
| --- | ---: |
| INC-001 — correlation only | 10 |
| INC-002 — confirmed deployment cause | 1 |
| INC-003 — confirmed dependency cause | 4 |
| INC-004 — inconclusive / abstention | 6 |

The two incidents requiring the greatest causal restraint — `INC-001` and `INC-004` — therefore account for:

```text
16 / 21
```

of all detected causal overclaims.

This is approximately:

```text
76%
```

of the observed causal findings.

The breadth benchmark is therefore exercising a different failure mode from simple factual hallucination.

The difficult question is often not whether a fact is present.

It is:

> How much authority does the available evidence justify?

---

# Finding 7 — Routing made model-dependent control flow visible

OpenAI and Anthropic produced the same routing trajectories:

```text
INC-001 -> deployment
INC-002 -> deployment
INC-003 -> dependency
INC-004 -> performance
```

Groq produced:

```text
INC-001 -> dependency
INC-002 -> deployment
```

before rate limits prevented observation of `INC-003` and `INC-004`.

The divergence on `INC-001` matters because it demonstrates that changing the provider/model bundle can change more than response wording.

It can change the selected workflow path.

For an architecture with model-owned routing:

> model behavior is part of control-plane behavior.

A route label is not itself a causal conclusion, and this experiment does not establish which `INC-001` route is universally correct.

The important observation is that provider/model choice changed execution control flow under the same fixture and routing architecture.

---

# Finding 8 — Evaluator-optimizer adapted, but self-evaluation did not guarantee causal correctness

OpenAI used the same evaluator-optimizer topology for every incident:

```text
generate
-> evaluate:1
-> quality-pass
```

Groq did the same for its two observable incidents.

Anthropic showed adaptive revision behavior.

For `INC-002` and `INC-003`:

```text
generate
-> evaluate:1
-> revise:1
-> evaluate:2
-> quality-pass
```

This required four model calls instead of two.

For `INC-001` and `INC-004`, Anthropic passed after the first evaluation.

The important counterexample is `INC-001`.

Anthropic evaluator-optimizer produced:

```text
100% specific grounding
2 detected causal overclaims
```

despite the internal evaluator issuing a quality pass without revision.

This supports an important design principle:

> An internal LLM evaluator is part of the generation architecture; it is not independent evidence that the final answer is correct.

External benchmark evaluation therefore remains necessary.

The breadth generation does not show that evaluator-optimizer is ineffective.

It shows that:

- it can alter control flow;
- it can trigger revisions;
- but its internal quality gate does not guarantee external causal correctness.

---

# Finding 9 — Evaluator-optimizer did not show a clear aggregate advantage over augmented generation

Across successful cells:

### Augmented

```text
97.8% grounding
3 causal overclaims
1.0 model call
1,264 mean tokens
7.69s p50
```

### Evaluator-optimizer

```text
97.6% grounding
4 causal overclaims
2.4 model calls
3,427 mean tokens
9.13s p50
```

The evaluator-optimizer used substantially more computation but did not improve aggregate grounding or causal findings over augmented generation in this breadth sample.

That does not establish that evaluator-optimizer is generally inefficient.

Its value may appear in tasks where revision targets are better aligned with the external quality objective.

The result supports a narrower engineering principle:

> Iterative evaluation loops should justify their additional cost with measured task-specific gains rather than being assumed to improve correctness by construction.

---

# Finding 10 — The uncertainty-language metric saturated

The benchmark field historically named:

```text
uncertainty_preserved
```

is implemented as lexical detection of uncertainty-related language.

In the breadth generation it returned true for:

```text
59 / 59
```

successful cells.

That includes:

- correlation-only incidents;
- confirmed-cause incidents;
- inconclusive incidents;
- responses with zero causal overclaims;
- responses with multiple causal overclaims.

The metric therefore did not discriminate correct epistemic posture in this experiment.

The final interpretation should call it:

```text
uncertainty-language detected
```

rather than treating it as proof that uncertainty was appropriately preserved.

This generation remains frozen.

The evaluator is not changed retroactively to improve the result.

A future evaluator generation may introduce posture-aware epistemic evaluation, but its outputs must remain separate from this frozen breadth generation.

---

# Provider-specific observations

## OpenAI

OpenAI completed all 24 cells.

Pattern results:

| Pattern | Grounding | Causal overclaims | Model calls | Tokens | p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Augmented | 100.0% | 1 | 1.0 | 947 | 7.38s |
| Chaining | 80.4% | 1 | 3.0 | 4,016 | 26.04s |
| Routing | 100.0% | 0 | 2.0 | 993 | 5.52s |
| Parallel | 98.2% | 3 | 4.0 | 5,172 | 20.60s |
| Evaluator-optimizer | 100.0% | 2 | 2.0 | 1,628 | 8.01s |
| Agent | 100.0% | 0 | 2.0 | 1,671 | 6.42s |

Within this bundle, routing and agent combined perfect specific grounding with zero detected causal overclaims.

Agent added tool-mediated evidence acquisition at a moderate token and latency increase relative to routing.

---

## Groq

Groq completed 12 of 24 cells.

The missing half of the matrix is entirely due to provider HTTP 429 responses across `INC-003` and `INC-004`.

Observed pattern results:

| Pattern | Observed | Grounding | Causal overclaims |
| --- | ---: | ---: | ---: |
| Augmented | 2/4 | 88.7% | 0 |
| Chaining | 2/4 | 61.3% | 0 |
| Routing | 2/4 | 79.9% | 1 |
| Parallel | 2/4 | 96.2% | 1 |
| Evaluator-optimizer | 2/4 | 88.0% | 0 |
| Agent | 2/4 | 92.9% | 0 |

These quality metrics describe only `INC-001` and `INC-002`.

They must not be interpreted as equivalent four-incident evidence.

In particular, Groq was not observed on `INC-004`, the strongest abstention-oriented fixture.

The Groq breadth generation therefore contributes both:

- quality observations for 12 successful cells;
- provider availability evidence for 12 rate-limited cells.

---

## Anthropic

Anthropic completed 23 of 24 cells.

Pattern results:

| Pattern | Observed | Grounding | Causal overclaims | Model calls | Tokens | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Augmented | 4/4 | 100.0% | 2 | 1.0 | 1,631 | 11.83s |
| Chaining | 3/4 | 75.2% | 4 | 3.0 | 6,004 | 36.61s |
| Routing | 4/4 | 92.0% | 1 | 2.0 | 2,007 | 14.22s |
| Parallel | 4/4 | 90.8% | 3 | 4.0 | 9,679 | 41.07s |
| Evaluator-optimizer | 4/4 | 100.0% | 2 | 3.0 | 5,715 | 26.69s |
| Agent | 4/4 | 92.0% | 0 | 2.0 | 4,365 | 17.36s |

Anthropic illustrates especially clearly why grounding alone is insufficient.

Augmented and evaluator-optimizer both achieved `100%` mean specific grounding while still producing causal overclaims.

The agent had lower mean grounding at `92.0%`, but no detected causal overclaims.

---

# Cost of additional structure

The breadth results do not show a monotonic relationship between more model calls and better quality.

Approximate architecture-level ordering by model calls was:

```text
augmented              1.0
routing                2.0
evaluator-optimizer    2.4
agent                  2.5
chaining               3.0
parallel               4.0
```

Yet grounding and causal discipline did not improve monotonically along that sequence.

Parallel had the most model calls and the largest token footprint, but also the largest number of causal overclaims.

Chaining required three sequential model calls but had the lowest grounding.

Agent used more system capabilities because it could call tools, but did not have the highest mean token use or latency.

This supports a broader architecture principle:

> Additional orchestration structure is a cost that should be justified by measured behavior, not an automatic quality improvement.

---

# Design implications

The breadth generation suggests the following design hypotheses for this incident-analysis domain.

## Use augmented generation as a strong low-complexity baseline

Augmented generation maintained excellent grounding at the lowest model-call count.

Its weakness was not factual coverage but occasional causal overreach.

## Use routing when differentiated control paths matter

Routing remained relatively efficient and exposed a real architectural property: model/provider choice can alter which execution path is selected.

Routing decisions therefore deserve explicit observability and evaluation.

## Do not assume sequential chaining improves reliability

Chaining was expensive, slow, and comparatively weak on grounding.

For evidence-sensitive tasks, sequential decomposition should be tested for inference propagation rather than assumed to provide additional safety.

## Treat parallel fan-out and final synthesis as separate risk surfaces

Parallelization can provide broad evidence coverage.

The final synthesis still requires strong causal constraints.

## Treat evaluator-optimizer as generation, not independent assurance

An internal evaluator can improve or revise outputs, but it shares model/system assumptions with the generator.

Independent evaluation remains necessary.

## Study bounded agents as controlled evidence-acquisition systems

The strongest observed agent property was not “more autonomy”.

It was:

```text
bounded actions
+ explicit read-only tools
+ finite execution budget
+ external evaluation
+ causal restraint
```

That combination deserves further investigation.

---

# Threats to validity

## 1. One run per cell

The breadth generation uses `n=1` per incident/pattern/provider cell.

It exposes breadth but not within-cell variance.

No statistical significance is claimed.

## 2. Provider availability was not uniform

Groq rate limits removed all observations for `INC-003` and `INC-004`.

Groq quality averages therefore cover a different incident subset from OpenAI and Anthropic.

## 3. Provider bundles differ

Model, transport, provider infrastructure, output limits, tokenization, reasoning configuration, and pacing differ.

Cross-provider results are bundle comparisons.

## 4. Token counts are not directly equivalent across providers

Raw token counts are useful primarily for within-provider architecture comparisons.

They are not normalized accounting units.

## 5. Live-service latency

Latency includes provider and network conditions at execution time.

It is not a service-level performance guarantee.

## 6. Grounding evaluation is bounded

Specific grounding does not mean complete semantic correctness.

A response can achieve perfect grounding while still making an unsupported causal inference.

## 7. Causal evaluation is benchmark-specific

Detected causal overclaims reflect the benchmark's labelled evidence and authority rules.

They should not be treated as a universal causal-reasoning metric.

## 8. Uncertainty-language detection saturated

The lexical uncertainty metric returned true for every successful cell.

It cannot distinguish correct epistemic adaptation in this generation.

## 9. Metadata-only persistence

Full model answers, prompts, evidence bodies, tool arguments, and tool results are intentionally not persisted in benchmark artifacts.

This improves the privacy and reproducibility boundary but limits unrestricted post-hoc semantic analysis.

## 10. Bounded agent scope

The agent is read-only and tightly bounded.

These results do not generalize to agents with mutation privileges, shell access, unrestricted tools, long horizons, or production control authority.

---

# What is not claimed

This experiment does not establish that:

- agents are universally better than workflows;
- agents are universally safer;
- one provider/model is universally superior;
- Groq has a 50% general availability rate;
- OpenAI is always more available;
- Anthropic is always slower;
- chaining is universally bad;
- parallelization inherently creates causal errors;
- evaluator-optimizer is ineffective;
- `100%` grounding means a completely correct answer;
- zero detected causal overclaims proves universal causal correctness;
- more tool use automatically improves reasoning;
- one observed trajectory is better than another;
- lexical uncertainty language proves correct epistemic posture.

---

# Main conclusion

The breadth generation does not identify a universal architecture winner.

It does show that architecture changes **what can fail**.

Sequential workflows can propagate inference across stages.

Parallel workflows can gather broad evidence while placing additional burden on synthesis.

Routing can make model behavior part of execution control.

Evaluator-optimizer loops can revise outputs without becoming independent assurance.

Tool-using agents can alter their own execution topology across provider/model bundles.

Within the observed breadth cells, the bounded agent was the only architecture pattern with no detected causal overclaims while maintaining high specific grounding.

That result is best interpreted as evidence for a narrower hypothesis:

> **Bounded autonomy may be valuable not because the system is allowed to do more, but because it can acquire evidence dynamically while operating inside explicit action, tool, and execution limits.**

The experiment supports further testing of that hypothesis.

It does not close the question.

---

# Reproducibility

Main frozen commit:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Main generation:

```text
72 attempted cells
59 successful cells
12 rate-limited cells
1 provider-error cell
```

Generated analysis artifacts include:

```text
analysis-manifest.json
availability-by-provider.csv
availability-by-provider-incident.csv
availability-summary.md
cells-72.csv
incident-pattern-provider-matrix.csv
provider-pattern-summary.csv
successful-trajectories.csv
architecture-summary.csv
incident-pattern-quality.csv
architecture-findings.md
causal-by-incident-pattern.csv
adaptive-control-flow.csv
```

Historical calibration generations remain separate and must not be recombined with this generation.
