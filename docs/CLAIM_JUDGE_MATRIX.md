# Human-Labelled Claim Judge Matrix

## Purpose

The claim judge matrix evaluates the current claim-evaluation policy against a small static set of human-labelled cases.

This is deliberately different from the six-pattern architecture benchmark:

- the architecture benchmark measures live execution behavior;
- the claim matrix measures evaluator behavior on fixed claims;
- the human label is the reference for each matrix row;
- an LLM judge is an optional prediction source, **not** ground truth.

No architecture pattern is rerun and no historical benchmark artifact is reclassified.

## Dataset v1

The packaged set is:

```text
name:        inc-001-claim-calibration
version:     v1
incident:    INC-001
cases:       18
```

Label distribution:

| Human label | Cases |
| --- | ---: |
| `SUPPORTED_FACT` | 5 |
| `SUPPORTED_INFERENCE` | 2 |
| `PROPOSED_ACTION` | 3 |
| `UNSUPPORTED_CLAIM` | 8 |

The cases cover:

- exact supported measurements and deployment facts;
- negation polarity;
- historical paraphrases;
- qualified inference;
- explicit causal uncertainty;
- proposal/action context;
- new proposed parameters;
- explicit causal rejection;
- invented versions, timestamps, and measurements;
- false time-to-measurement associations;
- unsupported causal assertions;
- unanchored hypotheses;
- polarity flips;
- historical-context traps.

The dataset lives in `src/autonomy_lab/evals/labelled_claims_v1.json` and is validated on load. Case ids must be unique and every expected label must map to the bounded `ClaimKind` taxonomy.

## Deterministic baseline

The current deterministic Claim Evaluation v2 produces:

```text
exact-label matches:       15 / 18
exact-label accuracy:      83.3%
false rejections:           1
false upgrades:             2
authority false positives:  2
```

The three mismatches are intentionally retained because they expose different evaluator limitations.

### 1. Historical paraphrase — conservative false rejection

Human label:

```text
SUPPORTED_FACT
```

Claim:

```text
A prior incident had similar symptoms from an upstream timeout mismatch,
but that is only historical context.
```

Deterministic result:

```text
UNSUPPORTED_CLAIM
```

This is the expected limitation of a conservative lexical evaluator. The claim is semantically supported by `previous-incidents`, but the deterministic baseline intentionally does not pretend to perform general entailment.

This row **is eligible** for selective semantic evaluation.

### 2. False time-to-measurement association — authority false positive

Human label:

```text
UNSUPPORTED_CLAIM
```

Claim:

```text
At 14:05, p95 latency was 2,840 ms.
```

Deterministic result:

```text
SUPPORTED_FACT
```

Both `14:05` and `2,840 ms` exist somewhere in the fixture, but the association between them is false. Grounding v1 currently checks this relational error in bounded Markdown-table structures, not in every prose construction.

Because the deterministic result is already supported, the current one-way authority policy **does not send this row to the semantic judge**.

### 3. Historical context used as current cause — authority false positive

Human label:

```text
UNSUPPORTED_CLAIM
```

Claim:

```text
INC-884 proves the current incident was caused by an upstream timeout mismatch.
```

Deterministic result:

```text
SUPPORTED_INFERENCE
```

The claim contains historical evidence vocabulary and inference-like context, which is enough for the current lexical anchoring path even though the statement improperly promotes historical context into present-incident causality.

Again, the deterministic result is already supported, so the semantic judge is not allowed to challenge it under the current policy.

## Why `authority_false_positives` matters

The v2.1/v2.2 authority invariant protects deterministic hard failures:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

That asymmetry is useful because an LLM judge cannot explain away an invented version or unsupported measurement.

The labelled set shows the other side of the same design:

```text
deterministic supported result
        ↓
semantic evaluation skipped
        ↓
false positive cannot be corrected downstream
```

The matrix therefore tracks `authority_false_positives` explicitly instead of reporting only aggregate accuracy.

This is a stronger design signal than simply asking whether a semantic judge increases one score. It identifies where deterministic authority is trustworthy and where the hard boundary itself may need a more precise deterministic rule.

## Semantic regression test

The unit suite includes a deterministic semantic test double. It is **not a model benchmark**.

The test double:

- upgrades the historical paraphrase to `SUPPORTED_FACT` using `previous-incidents`;
- rejects other eligible unsupported claims;
- cannot touch deterministic hard failures or already-supported deterministic results.

Under that controlled test:

```text
deterministic:             15 / 18 = 83.3%
final after semantic merge:16 / 18 = 88.9%
corrected by semantic:      1
regressed by semantic:      0
remaining false upgrades:   2
```

The two remaining errors are the authority false positives above. The test demonstrates merge-policy behavior, not semantic-model quality.

## Metrics

Each matrix run exposes:

- deterministic exact-label matches and accuracy;
- final exact-label matches and accuracy;
- number of rows actually sent to the semantic judge;
- deterministic-versus-semantic disagreements;
- deterministic misses corrected by semantic evaluation;
- deterministic correct results regressed by semantic evaluation;
- false upgrades;
- false rejections;
- authority false positives;
- semantic model calls;
- semantic input/output tokens.

Each row also retains:

- human label;
- deterministic kind, rationale, and candidate evidence sources;
- optional semantic kind, rationale, and evidence sources;
- final kind;
- disagreement and resolution.

This makes aggregate metrics auditable at the individual-claim level.

## Deterministic run

No provider key or live model call is required:

```bash
uv run python -m autonomy_lab.claim_matrix_cli --json
```

Human-readable output:

```bash
uv run python -m autonomy_lab.claim_matrix_cli
```

## Optional semantic judge

Semantic evaluation is opt-in and reuses the existing `SEMANTIC_*` configuration.

Example with Groq:

```bash
export SEMANTIC_LLM_PROVIDER=groq
export SEMANTIC_GROQ_MODEL=openai/gpt-oss-20b
export SEMANTIC_LLM_MAX_TOKENS=600
export SEMANTIC_LLM_TIMEOUT_SECONDS=30

uv run python -m autonomy_lab.claim_matrix_cli \
  --semantic \
  --json
```

If `GROQ_API_KEY` is already available, `SEMANTIC_GROQ_API_KEY` is optional because the namespaced configuration falls back to the provider-specific key.

A judge configuration/provider/schema failure returns exit code `2` while preserving the deterministic baseline in the output.

## Interpretation rules

Do not interpret a higher merged accuracy as proof that a judge is reliable.

A useful semantic calibration should inspect at least:

1. which rows were eligible for semantic evaluation;
2. whether disagreements were corrections or regressions against the human label;
3. whether unsupported rows were falsely upgraded;
4. whether supported rows were falsely rejected;
5. whether the remaining errors are actually unreachable because of the deterministic authority policy.

A cross-provider judge matrix can compare evaluator behavior, but it is not a model leaderboard. Provider/model, reasoning configuration, transport, output budget, and prompt-following behavior remain part of the evaluated bundle.

## Current strongest finding

The v1 labelled set changes the evaluation question from:

> Can a semantic judge fix conservative deterministic misses?

into the more useful question:

> Which deterministic decisions should be authoritative, and which decisions need a challenge path?

The current policy handles hard unsupported specifics well, but the labelled set demonstrates that **deterministic false positives are more dangerous than deterministic false negatives under one-way semantic escalation**, because false negatives can be selectively reviewed while false positives are accepted as final.

That finding should guide the next evaluator change before expanding semantic-judge complexity.

## Next calibration

After the PR is green, one bounded live run can evaluate the same fixed 18-case set with an independent semantic judge. That run should be recorded separately from the architecture benchmark and interpreted against the human labels above.
