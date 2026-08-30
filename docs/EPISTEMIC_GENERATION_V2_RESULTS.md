# Epistemic Benchmark Generation v2 Results

## Purpose

This document reports the first live benchmark generation using Epistemic Evaluation v4.1.

The generation asks a narrower question than the historical breadth benchmark:

> Does posture-aware evaluation change what the architecture comparison reveals when the evidence grants different amounts of causal authority?

The experiment remains descriptive:

```text
4 incidents × 6 patterns × 1 run × 3 provider/model/configuration bundles = 72 attempted cells
```

There is one run per cell. These results support architecture-oriented observations and hypotheses, not statistical significance claims.

---

## Frozen experimental boundary

The generation was frozen at:

```text
06e108f5ed7bc3a74e01682538a4bcd23f7d3023
```

This commit contains:

- `benchmark-record-v2`;
- `benchmark-summary-v2`;
- `breadth-v2`;
- Grounding Evaluation v1;
- Epistemic Evaluation v4.1;
- the dedicated `autonomy-lab-epistemic-benchmark` runner.

Historical breadth-v1 outputs remain unchanged and are not mixed into this generation.

---

## Canonical evidence postures

| Incident | Expected posture |
| --- | --- |
| `INC-001` | correlational — causal hypotheses must remain qualified |
| `INC-002` | confirmed cause — supported cause may be stated directly |
| `INC-003` | confirmed cause — supported cause may be stated directly |
| `INC-004` | inconclusive — explicit causal abstention is expected |

The evaluator infers these postures from fixture evidence rather than hard-coding verdicts by incident identifier.

---

## Provider bundles

The live generation intentionally reused the historical breadth provider/model/configuration bundles as closely as possible.

| Bundle | Model | Max output tokens | Timeout | Reasoning | Attempt interval |
| --- | --- | ---: | ---: | --- | ---: |
| OpenAI | `gpt-5.6-luna` | 4000 | 60s | provider-defined/default | 2s |
| Anthropic | `claude-sonnet-5` | 4000 | 60s | provider-defined/default | 10s |
| Groq | `openai/gpt-oss-20b` | 900 | 30s | medium | 30s |

Provider, model, transport, tokenization, output limits, reasoning configuration, and live-service conditions are part of each tested bundle.

Cross-provider comparisons therefore describe provider/model/API/configuration bundles, not isolated model quality.

---

# Availability before quality

Availability remains separate from answer quality.

| Provider | Attempts | Successful | Rate limited | Provider error | Completion |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 0 | 0 | 100.0% |
| Anthropic | 24 | 24 | 0 | 0 | 100.0% |
| Groq | 24 | 22 | 1 | 1 | 91.7% |
| **Total** | **72** | **70** | **1** | **1** | **97.2%** |

The two non-OK Groq cells are preserved as runtime/availability evidence. They are not converted into quality zeros and are not rerun in isolation to complete the matrix.

---

# Epistemic verdicts across successful cells

Only `status=ok` cells contribute to the verdict counts below.

| Verdict | Count | Share of 70 successful cells |
| --- | ---: | ---: |
| `aligned` | 20 | 28.6% |
| `overclaimed` | 41 | 58.6% |
| `no-position` | 6 | 8.6% |
| `over-hedged` | 3 | 4.3% |
| `insufficient-abstention` | 0 | 0.0% |

These are **detected verdicts under Epistemic v4.1**. The evaluator is deterministic and intentionally conservative; it is not semantic entailment or universal proof that a response is causally correct or incorrect.

---

# Incident-level posture results

| Incident | Observed | Aligned | Overclaimed | No-position | Over-hedged |
| --- | ---: | ---: | ---: | ---: | ---: |
| `INC-001` correlational | 18/18 | 2 | 16 | 0 | 0 |
| `INC-002` confirmed cause | 17/18 | 8 | 6 | 2 | 1 |
| `INC-003` confirmed cause | 17/18 | 7 | 6 | 2 | 2 |
| `INC-004` inconclusive | 18/18 | 3 | 13 | 2 | 0 |

The two incidents requiring the greatest restraint — `INC-001` and `INC-004` — account for:

```text
29 / 41 detected overclaims
```

or approximately:

```text
70.7%
```

of all `overclaimed` verdicts in successful cells.

This concentration appeared across all three provider/model/configuration bundles.

The supported observation is therefore narrower than “models overclaim in general”:

> In this generation, the deterministic posture-aware evaluator detected substantially more causal-authority mismatch in the correlation-only and explicit-abstention incidents than in the two confirmed-cause incidents.

---

# Architecture-level epistemic results

| Pattern | Observed | Aligned | Alignment rate | Overclaimed | Overclaim rate | Other verdicts |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Augmented | 12/12 | 5 | 41.7% | 5 | 41.7% | 2 no-position |
| Chaining | 12/12 | 3 | 25.0% | 9 | 75.0% | — |
| Routing | 12/12 | 1 | 8.3% | 11 | 91.7% | — |
| Parallel | 11/12 | 2 | 18.2% | 6 | 54.5% | 2 no-position, 1 over-hedged |
| Evaluator-optimizer | 11/12 | 4 | 36.4% | 6 | 54.5% | 1 over-hedged |
| Agent | 12/12 | 5 | 41.7% | **4** | **33.3%** | 2 no-position, 1 over-hedged |

Within the fully observed patterns, bounded tool-using agency had the lowest detected overclaim rate in this generation.

That result should be stated carefully:

> Across the 12 observed bounded-agent cells, Epistemic v4.1 detected four overclaims, compared with five for augmented generation, nine for chaining, and eleven for routing.

This does **not** establish that agents are universally safer or better. It supports further study of bounded evidence acquisition and model-owned control flow as possible contributors to causal restraint under these fixtures.

---

# Grounding and epistemic posture remain distinct

Weighted across successful provider cells, mean Grounding v1 ratios were approximately:

| Pattern | Observed | Mean grounding |
| --- | ---: | ---: |
| Augmented | 12 | 97.5% |
| Chaining | 12 | 88.8% |
| Routing | 12 | 95.1% |
| Parallel | 11 | 85.7% |
| Evaluator-optimizer | 11 | 97.0% |
| Agent | 12 | 96.7% |

The architecture with the highest grounding is not automatically the architecture with the strongest posture alignment.

Routing is the clearest example in this generation: it retained high mean grounding while receiving eleven `overclaimed` verdicts across twelve observed cells.

This reinforces the project's core separation between:

1. whether specific facts are grounded in the bounded evidence;
2. how much causal authority the final answer claims from those facts.

---

# Provider-level verdicts

| Provider | Successful | Aligned | Overclaimed | No-position | Over-hedged |
| --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 24 | 8 | 13 | 2 | 1 |
| Anthropic | 24 | 7 | 16 | 0 | 1 |
| Groq | 22 | 5 | 12 | 4 | 1 |

The same broad concentration in `INC-001` and `INC-004` appeared under all three bundles.

This makes the signal less likely to be only a single-provider behavior, but it still does not establish provider-independent statistical significance because `n=1` per cell.

---

# Important evaluator limitation

Epistemic v4.1 composes with Grounding v1.

A Grounding v1 causal-overclaim finding is authoritative for v4.1 and maps to `overclaimed`.

Grounding v1 is deterministic and uses lexical/evidence matching to decide whether a current causal claim is explicitly supported by a confirmed-cause fixture. Therefore some `overclaimed` verdicts in `INC-002` and `INC-003` may reflect the conservative deterministic matching boundary rather than a semantically invalid causal claim.

For that reason, the correct public language is:

```text
detected epistemic overclaim under Epistemic v4.1
```

not:

```text
proven causal error
```

A future labelled semantic calibration may test this boundary without rewriting this frozen generation.

---

# What this generation supports

The strongest supported observations are:

1. posture-aware evaluation exposes distinctions that lexical uncertainty detection did not;
2. correlation-only and explicit-abstention fixtures concentrated detected causal-authority mismatch;
3. grounding and epistemic posture are separate evaluation dimensions;
4. routing showed high grounding but a high detected-overclaim rate;
5. bounded tool-using agency had the lowest detected-overclaim rate among the fully observed patterns in this generation;
6. provider/model/configuration choice remains part of both runtime behavior and output posture;
7. availability must remain separate from quality.

---

# Explicit non-claims

This generation does **not** establish that:

- agents are universally safer or more accurate than workflows;
- routing is universally unsafe;
- a deterministic `overclaimed` verdict proves semantic causal error;
- any provider is intrinsically more or less reliable from this one run window;
- the provider/model bundles are pure model comparisons;
- one run per cell is statistically significant;
- Grounding v1 or Epistemic v4.1 is a complete factuality or causal-reasoning metric.

---

# Generation integrity

Each provider generation was produced from the same frozen implementation commit and stored as metadata-only benchmark artifacts.

For every provider directory, SHA-256 checksums were generated after the run and verified successfully.

The generation retains metadata such as:

- provider/model/configuration provenance;
- status;
- token and latency metadata;
- Grounding v1 findings/counts;
- Epistemic v4.1 posture and verdict fields;
- coarse trajectory metadata.

It does not intentionally persist:

- full prompts;
- full model answers;
- evidence bodies in benchmark result records;
- tool arguments/results;
- credentials or API keys.

---

# Next step

The next publication step is a curated metadata-only evidence pack containing:

1. the three provider generation manifests;
2. all 72 metadata-only benchmark records;
3. canonical consolidated cells;
4. availability summaries;
5. incident/pattern/provider epistemic summaries;
6. Grounding v1 × Epistemic v4.1 comparison tables;
7. trajectory metadata;
8. recursive persistence-safety validation;
9. SHA-256 checksums.

The evidence pack must be derived from the frozen local generation outputs without rerunning any model calls.
