# Deterministic Authority False-Positive Hardening

## Purpose

The human-labelled claim matrix exposed a failure mode that matters specifically because the semantic policy is intentionally one-way:

```text
deterministic supported result
        ↓
semantic evaluation skipped
        ↓
false positive becomes final
```

The v1 matrix originally measured two such `authority_false_positives`:

1. a false time-to-measurement association built from individually valid values;
2. historical incident evidence promoted into a cause for the current incident.

This change hardens those two boundaries deterministically rather than broadening LLM-judge authority.

## Before

Human-labelled set v1:

```text
cases:                       18
deterministic correct:       15 / 18
deterministic accuracy:      83.3%
false rejections:             1
false upgrades:               2
authority false positives:    2
```

The remaining deterministic false negative was the intentionally conservative historical paraphrase. The semantic judge could review that miss, but it could not challenge the two already-supported false positives.

## Guard 1 — explicit prose time/measurement association

Failure case:

```text
At 14:05, p95 latency was 2,840 ms.
```

Both values appear independently in the fixture, but the exact pair does not. `2,840 ms` belongs to `14:10`.

The new guard is intentionally narrow. It rejects only when:

- exactly one timestamp is present in the claim;
- exactly one measurement is present;
- the measurement itself exists in the bounded fixture;
- the wording explicitly relates the timestamp and measurement (`at`, `:`, `=`, arrow-like relation);
- the exact normalized pair is absent from fixture associations.

A supported pair remains supported:

```text
At 14:10, p95 latency was 2,840 ms.
```

A multi-pair sentence is not interpreted by this narrow rule. This avoids pretending that a lexical guard can perform general relation extraction.

## Guard 2 — historical evidence promoted into current causality

Failure case:

```text
INC-884 proves the current incident was caused by an upstream timeout mismatch.
```

The historical evidence does support the statement that INC-884 involved an upstream timeout mismatch. It does **not** establish the cause of INC-001.

The new guard rejects a claim only when:

- it references a known historical incident id from the bounded evidence;
- the claim explicitly targets the `current` or `this` incident/outage/event;
- unqualified causal language applies to that current context within a bounded span;
- no explicit causal rejection is present.

The following remains allowed by this guard:

```text
INC-884 had similar symptoms caused by an upstream timeout mismatch;
the current incident remains unconfirmed.
```

And explicit rejection remains allowed:

```text
INC-884 does not prove the current incident was caused by an upstream timeout mismatch.
```

## Authority policy

The two new rationales are:

```text
deterministic-authority-unsupported-association
deterministic-authority-historical-current-causality
```

They are treated as deterministic hard failures by Semantic Claim Evaluation v2.1. The semantic judge is therefore not allowed to upgrade them.

This preserves the original policy goal: semantic evaluation may recover conservative soft misses, but it cannot explain away bounded deterministic contradictions.

## After

The unchanged 18-case human-labelled set now produces:

```text
cases:                       18
deterministic correct:       17 / 18
deterministic accuracy:      94.4%
false rejections:             1
false upgrades:               0
authority false positives:    0
```

With the deterministic semantic test double used only to verify merge-policy behavior:

```text
final correct:               18 / 18
final accuracy:              100.0%
corrected by semantic:        1
regressed by semantic:        0
false rejections:             0
false upgrades:               0
authority false positives:    0
semantic evaluated:           3
semantic model calls:         3
```

The single semantic correction remains the historical paraphrase that the deterministic evaluator intentionally leaves conservative.

This 100% result is **not** a claim of general evaluator accuracy. It is exact-label accuracy on the fixed 18-case calibration set and must be interpreted only within that bounded set.

## Why not broaden semantic authority instead?

Allowing the judge to challenge every deterministic supported result would make the aggregate matrix easier to improve, but would weaken the project's core control boundary.

The better response to an authority false positive is first to ask whether a bounded deterministic rule can represent the missing invariant. In these two cases it can:

- evidence relationships matter, not just value membership;
- historical causality and current causality are different scopes.

Only failure modes that cannot be represented safely with bounded deterministic rules should motivate a broader challenge architecture.

## Validation

The implementation is covered by direct guard tests plus the complete human-labelled matrix.

Current quality evidence:

- Ruff lint and format: pass;
- architecture validation: pass;
- strict MyPy: pass;
- tests: **134 passed**;
- coverage: **86.53%**;
- Bandit: pass;
- pip-audit: no known vulnerabilities.

## Benchmark boundary

The frozen 90-run OpenAI/Groq/Anthropic architecture benchmark is unchanged. No historical benchmark run is reclassified by this evaluator hardening.

The benchmark and the human-labelled evaluator calibration remain separate experimental layers.
