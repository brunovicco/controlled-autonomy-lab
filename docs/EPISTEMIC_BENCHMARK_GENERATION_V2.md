# Epistemic Benchmark Generation v2

## Status

This document defines the next benchmark-generation protocol after Epistemic Evaluation v4.1.

The implementation PR that introduces this runner must not itself be treated as a live benchmark generation. Provider calls begin only after the implementation is merged, the quality gate is green, and a new freeze commit is explicitly selected.

Historical benchmark outputs remain unchanged.

---

## Purpose

The historical breadth generation recorded Grounding Evaluation v1 metadata, including the lexical field `uncertainty_preserved`.

Epistemic Benchmark v2 adds posture-aware metadata without retaining full model answers.

Every successful v2 cell can record:

- expected evidence posture;
- epistemic verdict;
- aligned/not-aligned flag;
- direct causal assertion detection;
- hedged causal-language detection;
- explicit abstention detection;
- uncertainty-language detection;
- the existing Grounding v1 causal-overclaim count.

The answer itself is still not persisted in benchmark artifacts.

---

## Schema provenance

New artifacts declare their provenance explicitly:

```text
record schema:        benchmark-record-v2
summary schema:       benchmark-summary-v2
breadth manifest:     breadth-v2
grounding evaluator:  grounding-v1
epistemic evaluator:  epistemic-v4.1
```

A `benchmark-record-v2` record may have `epistemic_evaluation_version = null` when produced by the historical benchmark runner without the new evaluator.

The dedicated v2 generation runner always configures:

```text
epistemic_evaluation_version = epistemic-v4.1
```

and refuses mismatched callback/version combinations before provider calls.

---

## Dedicated runner

The new generation uses a separate console entry point:

```bash
uv run autonomy-lab-epistemic-benchmark
```

This is intentionally separate from the historical `autonomy-lab benchmark` command so that a new evaluator is not silently introduced into an old experimental protocol.

Single incident:

```bash
uv run autonomy-lab-epistemic-benchmark \
  --incident INC-004 \
  --runs 1 \
  --output results/epistemic-v4-1-inc004
```

Canonical breadth suite:

```bash
uv run autonomy-lab-epistemic-benchmark \
  --all-incidents \
  --runs 1 \
  --output results/epistemic-v4-1-breadth
```

The breadth suite retains the existing four canonical incidents and rotates the first pattern by incident.

---

## Freeze procedure

Before any paid/provider-backed run:

```bash
git status --short
git rev-parse HEAD
```

The worktree should be clean and the selected commit should be recorded as the generation freeze.

For explicit provenance, the runner also supports the existing environment override used by benchmark metadata collection:

```bash
export AUTONOMY_LAB_GIT_COMMIT="$(git rev-parse HEAD)"
```

Provider/model/token/timeout/interval settings must be frozen per generation. API keys remain local and must never be committed.

---

## Availability is not quality

The v2 manifest counts these outcomes separately:

- `ok`;
- `rate_limited`;
- `provider_error`;
- `bound_exceeded`.

Only `status=ok` cells can carry grounding or epistemic quality verdicts.

Rate limits, provider errors, and bounded-agent exhaustion are availability/runtime evidence. They are not imputed as quality zeros.

A failed cell keeps evaluator-version provenance but has no epistemic verdict.

---

## Epistemic aggregates

Per-pattern summaries include:

- `epistemic_evaluated`;
- `epistemic_aligned`;
- `epistemic_alignment_rate`;
- `epistemic_overclaimed`;
- `epistemic_over_hedged`;
- `epistemic_insufficient_abstention`;
- `epistemic_no_position`.

The alignment-rate denominator is only cells that actually contain an epistemic verdict.

Do not use provider failures or bound exhaustion in that denominator.

---

## Generation boundary

Do not append v2 verdicts to the frozen breadth-v1 rows as if the evaluator had existed at generation time.

Do not combine pre-fix and post-fix generations.

Do not rerun only failed cells and then present the mixed set as one homogeneous generation.

If a real runner or evaluator defect is discovered during a live generation:

1. preserve the observed output;
2. stop interpretation;
3. fix the defect in a separate branch/PR with regression coverage;
4. merge only after review;
5. select a new freeze commit;
6. rerun the full intended experiment as a new generation.

---

## First live-use recommendation

The first provider-backed v2 experiment should remain descriptive and small:

```text
4 incidents × 6 patterns × 1 run × provider bundles
```

The goal is not to reproduce a model leaderboard. It is to test whether posture-aware evaluation changes what the architecture comparison reveals, especially for:

- correlation without confirmed causality (`INC-001`);
- confirmed causes (`INC-002`, `INC-003`);
- required abstention (`INC-004`).

With `n=1` per cell, findings remain descriptive evidence rather than statistical significance claims.
