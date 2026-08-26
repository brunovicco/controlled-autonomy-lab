# Grounding Evaluation v1

Grounding Evaluation v1 adds a deterministic quality signal to the architecture comparison.

Its purpose is narrow: identify exact unsupported factual specifics, distinguish proposed action parameters, and flag unqualified causal claims by comparing a model answer with the bounded incident fixture already used by every pattern.

It does **not** call another LLM. The fixture remains the source of truth.

## Why deterministic first

The evaluator-optimizer pattern already demonstrates that an LLM evaluator can accept an answer that still contains unsupported specifics. For this reason, Grounding Evaluation v1 does not use LLM-as-a-judge as the primary oracle.

The first version intentionally favors checks that are explainable and reproducible:

- semantic versions such as `v2.18.4`;
- timestamps such as `14:10`;
- measurements and durations such as `2840ms`, `8.7%`, `3 s`, or `30-60 min`;
- percentage-point deltas that can be derived exactly from fixture percentages;
- strong causal language without local or section-level uncertainty qualifiers;
- whether the answer preserves explicit uncertainty language;
- whether an otherwise unsupported time/measurement appears under a recommendation/action section rather than as an observed fact.

Timestamp spans are excluded from measurement parsing. This prevents text such as `13:55 % 5xx = 0.2 %` from incorrectly producing an invented `55%` measurement.

## Finding types

| Finding | Meaning |
| --- | --- |
| `unsupported-version` | a concrete version appears in the answer but not in the incident/evidence fixture |
| `unsupported-time` | a timestamp is presented outside a proposal section but does not exist in the fixture |
| `unsupported-measurement` | a factual measurement, percentage, or duration is neither present nor explicitly derivable from the fixture |
| `proposed-parameter` | an otherwise unsupported timestamp/measurement occurs under a recommendation/action heading and is tracked separately from factual grounding |
| `causality-overclaim` | strong causal language appears without a local or section-level uncertainty qualifier |

Examples:

```text
v2.18.4      -> supported
v2.18.3      -> unsupported-version
2840ms       -> supported
2 840 ms     -> supported after Unicode normalization
1250ms       -> unsupported-measurement
"p95 was 1 s" -> unsupported-measurement
"alert if p95 > 1 s" under Recommended next steps -> proposed-parameter
8.5 pp       -> supported because 8.7% - 0.2% = 8.5 percentage points
```

Concrete semantic versions remain checkable even inside recommendations. For example, `roll back to v2.18.3` is still reported when the fixture never identifies `v2.18.3` as an available previous release.

The evaluator deduplicates repeated unsupported specifics so one invented value repeated multiple times does not artificially inflate the score.

## Proposed parameters versus unsupported facts

A benchmark should not treat every new number as a hallucinated fact. A model may legitimately propose a reversible monitoring window or alert threshold that is not part of the incident evidence.

Grounding Evaluation v1 therefore uses Markdown section structure as a deterministic signal. Under headings such as `Recommended next steps`, `Actions`, `Plan`, `Checks`, `Mitigation`, or `Remediation`, new times and measurements are classified as `proposed-parameter`.

For example:

```text
## Recommended next steps
Monitor for 15-30 minutes.
Alert if error rate exceeds 5%.
```

The `15-30 minutes` and `5%` values are visible in the report but do not lower the factual specific-grounding ratio.

This is intentionally structural rather than semantic. A free-form recommendation outside a recognizable section can still be classified as unsupported in v1.

## Causality and uncertainty

The incident fixture deliberately contains correlation without proven causality. Grounding Evaluation v1 therefore distinguishes these forms:

```text
The deployment caused the incident.
```

This is reported as `causality-overclaim`.

```text
## Hypotheses (not proven)
The new timeout is too low, causing downstream timeouts.
```

The heading explicitly qualifies the section as hypothetical, so the causal phrase is not reported as an overclaim.

Likewise:

```text
Hypothesis: the deployment may have caused the increase, but the timing is only correlation.
```

preserves uncertainty.

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

- `unsupported`: number of unique unsupported factual specifics;
- `proposed`: number of new action parameters tracked separately;
- `causality`: number of unqualified causal overclaims;
- `uncertainty`: whether explicit uncertainty language was preserved;
- `status`: `ok`, `rate_limited`, or `provider_error`.

## Partial benchmark behavior

A provider failure in one architecture should not erase completed results from the others. `compare` therefore fails soft at the pattern boundary.

If a provider returns a rate limit response, the affected row is emitted as:

```text
chaining | - | - | - | - | - | - | - | - | - | rate_limited
```

and the loop continues with the remaining patterns. Other provider failures are shown as `provider_error`.

The command returns exit code `2` when at least one pattern could not complete. This makes an incomplete benchmark observable to scripts/CI while preserving the partial table for analysis. Grounding Evaluation v1 deliberately does not hide rate limiting with automatic retries because retry delays would change benchmark latency semantics.

## Specific grounding ratio

For single-run reports, the evaluator exposes:

```text
supported factual specifics / (supported factual specifics + unsupported factual specifics)
```

`proposed-parameter` findings are deliberately excluded from this denominator.

A value of `1.0` means every exact factual specific checked by v1 was supported or explicitly derivable. It does **not** mean the whole answer is factually correct.

This ratio is deliberately not treated as a universal quality score: a vague answer can contain few checkable specifics and still obtain a high ratio.

## What v1 does not detect

Grounding Evaluation v1 is not a complete hallucination detector. It does not attempt to prove:

- semantic correctness of every prose claim;
- whether a recommended action or proposed parameter is operationally appropriate;
- whether a newly proposed component, tool, or architecture is a good idea;
- whether an inference is logically valid when it contains no exact checked specific;
- whether an answer omitted important evidence;
- whether an LLM evaluator made a good judgment.

For example, proposing a circuit breaker is a recommendation, not automatically an unsupported fact. Conversely, stating `the previous timeout was 3 s` as an observed fact is checkable and is reported when the fixture contains no such value.

## Trace boundary

Grounding findings are derived from answer content and are shown only in the CLI/JSON result when requested. They are not added to the metadata-only trace file, which continues to exclude prompts, answers, evidence bodies, tool arguments/results, and credentials.

## Future work

Potential later phases can add semantic claim classification, omission/coverage metrics, or an optional LLM judge as a secondary signal. Any model-based evaluator should remain separate from the deterministic fixture checks so disagreement between the two is observable rather than hidden.
