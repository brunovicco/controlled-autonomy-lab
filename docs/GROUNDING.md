# Grounding Evaluation v1

Grounding Evaluation v1 adds a deterministic quality signal to the architecture comparison.

Its purpose is narrow: identify exact unsupported specifics and unqualified causal claims in a model answer by comparing that answer with the bounded incident fixture already used by every pattern.

It does **not** call another LLM. The fixture remains the source of truth.

## Why deterministic first

The evaluator-optimizer pattern already demonstrates that an LLM evaluator can accept an answer that still contains unsupported specifics. For this reason, Grounding Evaluation v1 does not use LLM-as-a-judge as the primary oracle.

The first version intentionally favors checks that are explainable and reproducible:

- semantic versions such as `v2.18.4`;
- timestamps such as `14:10`;
- measurements and durations such as `2840ms`, `8.7%`, `3 s`, or `30–60 min`;
- percentage-point deltas that can be derived exactly from fixture percentages;
- strong causal language without nearby uncertainty qualifiers;
- whether the answer preserves any explicit uncertainty language.

## Finding types

| Finding | Meaning |
| --- | --- |
| `unsupported-version` | a version appears in the answer but not in the incident/evidence fixture |
| `unsupported-time` | a timestamp appears in the answer but not in the fixture |
| `unsupported-measurement` | a measurement, percentage, or duration appears in the answer but is neither present nor explicitly derivable from the fixture |
| `causality-overclaim` | strong causal language appears without a local uncertainty qualifier |

Examples:

```text
v2.18.4      -> supported
v2.18.3      -> unsupported-version
2840ms       -> supported
2 840 ms     -> supported after Unicode normalization
1250ms       -> unsupported-measurement
3 s          -> unsupported-measurement
30–60 min    -> unsupported-measurement
8.5 pp       -> supported because 8.7% - 0.2% = 8.5 percentage points
```

The evaluator deduplicates repeated unsupported specifics so one invented value repeated multiple times does not artificially inflate the score.

## Causality and uncertainty

The incident fixture deliberately contains correlation without proven causality. Grounding Evaluation v1 therefore distinguishes these two forms:

```text
The deployment caused the incident.
```

This is reported as `causality-overclaim`.

```text
Hypothesis: the deployment may have caused the increase, but the timing is only correlation.
```

This preserves uncertainty and is not reported as a causal overclaim.

The causal check is intentionally conservative and lexical. It is not a general natural-language inference engine.

## CLI

Evaluate a single live run:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding
```

JSON output includes a structured grounding report:

```bash
uv run autonomy-lab run agent --incident INC-001 --grounding --json
```

`compare` evaluates grounding for every architecture automatically:

```bash
uv run autonomy-lab compare --incident INC-001
```

The table adds:

- `unsupported`: number of unique unsupported specifics;
- `causality`: number of unqualified causal overclaims;
- `uncertainty`: whether explicit uncertainty language was preserved.

## Specific grounding ratio

For single-run reports, the evaluator also exposes:

```text
supported specifics / (supported specifics + unsupported specifics)
```

A value of `1.0` means that every exact specific checked by v1 was supported or explicitly derivable. It does **not** mean the whole answer is factually correct.

This ratio is deliberately not treated as a universal quality score: a vague answer can contain few checkable specifics and still obtain a high ratio.

## What v1 does not detect

Grounding Evaluation v1 is not a complete hallucination detector. It does not attempt to prove:

- semantic correctness of every prose claim;
- whether a recommended action is operationally appropriate;
- whether a newly proposed component, tool, or architecture is a good idea;
- whether an inference is logically valid when it contains no exact checked specific;
- whether an answer omitted important evidence;
- whether an LLM evaluator made a good judgment.

For example, proposing a circuit breaker is a recommendation, not automatically an unsupported fact. Conversely, claiming that a previous timeout was `3 s` is checkable and is reported when the fixture contains no such value.

## Trace boundary

Grounding findings are derived from answer content and are shown only in the CLI/JSON result when requested. They are not added to the metadata-only trace file, which continues to exclude prompts, answers, evidence bodies, tool arguments/results, and credentials.

## Future work

Potential later phases can add semantic claim classification, omission/coverage metrics, or an optional LLM judge as a secondary signal. Any model-based evaluator should remain separate from the deterministic fixture checks so disagreement between the two is observable rather than hidden.
