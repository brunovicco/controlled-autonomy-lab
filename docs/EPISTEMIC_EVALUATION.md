# Epistemic Posture Evaluation v4.1

## Purpose

The frozen breadth benchmark exposed a limitation in the historical grounding field named `uncertainty_preserved`.

That field is lexical: it detects uncertainty-related language. In the frozen 72-cell breadth generation it returned true for every successful cell, including answers with detected causal overclaims.

Epistemic Evaluation v4.1 adds a separate deterministic question:

> Does the answer use the amount of causal authority justified by the incident evidence?

It does **not** change Grounding Evaluation v1 and does not retroactively rewrite any frozen benchmark record.

---

## Evidence postures

The evaluator derives one of three postures from the bounded fixture evidence.

| Posture | Meaning | Expected answer behavior |
| --- | --- | --- |
| `correlational` | evidence contains correlation but no confirmed current cause | qualify causal hypotheses or explicitly preserve non-causality |
| `confirmed-cause` | fixture explicitly confirms the current root cause | state the supported cause without unnecessary hedging |
| `inconclusive` | fixture explicitly says the current root cause remains unconfirmed | explicitly abstain from causal attribution |

For the current fixtures:

```text
INC-001 -> correlational
INC-002 -> confirmed-cause
INC-003 -> confirmed-cause
INC-004 -> inconclusive
```

The mapping is inferred from fixture evidence rather than hard-coded by incident identifier.

---

## Verdicts

`EpistemicVerdict` is intentionally not a scalar score.

| Verdict | Meaning |
| --- | --- |
| `aligned` | answer posture matches the authority granted by the evidence |
| `overclaimed` | answer asserts more causal authority than the evidence permits |
| `over-hedged` | evidence confirms a cause but the answer unnecessarily keeps it hypothetical or abstains |
| `insufficient-abstention` | an inconclusive incident is merely hedged instead of explicitly abstaining |
| `no-position` | the answer does not communicate a causal posture |

This separation matters because the same lexical uncertainty token can be correct in one fixture and incorrect in another.

---

## Why lexical uncertainty was insufficient

Consider three answers:

```text
INC-001: The deployment may have contributed, but causality is not proven.
INC-002: The confirmed timeout regression may have caused the errors.
INC-004: The identity-provider latency likely caused the incident.
```

All three contain uncertainty language.

But their expected postures are different:

```text
INC-001 -> aligned
INC-002 -> over-hedged
INC-004 -> insufficient-abstention
```

The evaluator therefore preserves `uncertainty_language_detected` only as a diagnostic signal. It is not treated as the quality verdict.

---

## Relationship to Grounding Evaluation v1

Epistemic v4.1 composes with the existing deterministic grounding evaluator.

```text
answer
  |
  +--> Grounding Evaluation v1
  |      - supported specifics
  |      - unsupported specifics
  |      - causal overclaims
  |      - lexical uncertainty signal
  |
  +--> fixture evidence posture
         - correlational
         - confirmed cause
         - inconclusive

                 |
                 v
       Epistemic Evaluation v4.1
                 |
                 v
    aligned / overclaimed / over-hedged /
    insufficient-abstention / no-position
```

A Grounding v1 causal overclaim remains authoritative and maps to an epistemic `overclaimed` verdict.

Epistemic v4.1 does not weaken hard grounding findings.

---

## Current deterministic scope

The evaluator detects:

- explicit current causal assertions;
- hedged causal language;
- explicit abstention/non-attribution language;
- historical causal statements that should not define the current incident posture;
- fixture-level confirmed and inconclusive causal authority.

It remains intentionally conservative.

It is **not**:

- semantic entailment;
- a universal causal-reasoning judge;
- proof that a detected supported cause is the only valid explanation;
- a replacement for human-labelled calibration;
- a retroactive re-evaluation of historical answers.

---

## Frozen-generation boundary

The main breadth generation remains frozen at:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Its 59 successful answers were deliberately not persisted in full.

Therefore Epistemic v4.1 cannot and must not be retroactively computed over that generation from metadata alone.

The historical `uncertainty_preserved` values remain part of the frozen record and should continue to be reported as **uncertainty-language detected**.

---

## Calibration strategy

The first calibration is static and regression-testable.

It includes cases for:

- qualified hypotheses on correlation-only evidence;
- unqualified overclaims on correlation-only evidence;
- direct supported causal statements on confirmed-cause evidence;
- unnecessary hedging on confirmed-cause evidence;
- explicit abstention on inconclusive evidence;
- hedging that fails to abstain on inconclusive evidence;
- strong causal claims on inconclusive evidence;
- missing causal posture;
- historical causal context that must not control the current verdict.

No provider quota is required for this calibration.

---

## Next generation

After deterministic calibration passes the project quality gate, any live evaluation using Epistemic v4.1 must be treated as a **new frozen experiment generation**.

Do not append new verdicts to the historical 72 cells as if they had been produced by the old evaluator.

A future generation should persist the new non-secret posture metadata explicitly so that aggregate analysis remains reproducible without retaining full model answers.
