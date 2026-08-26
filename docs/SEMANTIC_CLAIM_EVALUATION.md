# Semantic Claim Evaluation v2.1

Semantic Claim Evaluation v2.1 is a secondary, opt-in analysis layer for claims that the deterministic v2 baseline deliberately leaves unsupported because it cannot perform semantic entailment.

It is not a replacement for Grounding v1 or deterministic Claim Evaluation v2.

## Why this layer exists

The first live Claim Evaluation v2 calibration produced one useful false negative:

> A prior incident had similar symptoms from an upstream timeout mismatch, but that is historical context—not proof of the current cause.

The bounded fixture states that `INC-884` had similar symptoms caused by an upstream timeout mismatch and explicitly says that this historical context is not evidence of the current root cause.

A human can see that the model answer is a faithful paraphrase. The deterministic evaluator intentionally cannot establish that semantic equivalence, so it classifies the claim as `UNSUPPORTED_CLAIM`.

v2.1 adds a bounded semantic judgement for this class of conservative miss.

## Authority model

Semantic evaluation is asymmetric. It may improve coverage, but it cannot weaken deterministic hard signals.

| Deterministic result | Semantic evaluation | Final authority |
| --- | --- | --- |
| `SUPPORTED_FACT` | skipped | deterministic |
| `SUPPORTED_INFERENCE` | skipped | deterministic |
| `PROPOSED_ACTION` | skipped | deterministic |
| `UNSUPPORTED_CLAIM` with `grounding-v1-*` rationale | skipped | deterministic hard failure |
| other `UNSUPPORTED_CLAIM` | eligible | merged semantic result |

The central invariant is:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

A semantic model cannot "explain away" an unsupported version, measurement, association, or causal overclaim detected by Grounding v1.

## Bounded semantic contract

Eligible claims are evaluated one at a time. The model receives only:

- the claim text;
- the bounded evidence source ids;
- the bounded evidence summaries already available for the incident.

The evaluator is instructed not to use outside knowledge.

It must return exactly one JSON object with these fields:

```json
{
  "verdict": "supported-fact | supported-inference | unsupported-claim",
  "rationale": "short reason",
  "evidence_sources": ["source-id"]
}
```

The adapter validates:

- exact JSON rather than Markdown-wrapped output;
- exact field names;
- the allowed verdict set;
- a non-empty bounded rationale;
- `evidence_sources` as a list of strings;
- every returned source id against the supplied bounded source set;
- at least one evidence source for a supported semantic verdict.

Malformed or unbounded semantic output is an evaluation failure, not permission to guess.

## Deterministic pre-filtering

Live calibration showed that not every deterministic miss needs an LLM. Two initially unsupported claims were near-verbatim facts already present in bounded `deployments` or `dependencies` evidence:

- the deployment included a new payment-provider timeout configuration;
- no confirmed payment-provider outage was reported.

The deterministic baseline therefore includes a deliberately narrow near-verbatim matcher for high-confidence deployment/dependency paraphrases before semantic escalation.

This matcher preserves negation polarity so a claim such as `confirmed outage` cannot be accepted from evidence that says `no confirmed outage`. It intentionally does not cover `previous-incidents`; historical evidence remains conservative because confusing a previous cause with the current incident is a materially different failure mode.

The semantic layer is therefore reserved for genuinely ambiguous conservative misses rather than acting as a general second pass over every claim.

## Merge output

The v2.1 result keeps three layers visible for each claim:

```text
deterministic result
semantic result (when eligible)
final merged result
```

It also records:

- `disagreement`;
- `resolution`;
- semantic model calls;
- semantic input tokens;
- semantic output tokens.

Semantic calls and token usage are kept separate from the architecture pattern's own `model_calls` and token accounting. Post-run evaluation therefore does not rewrite the execution cost of the pattern being studied.

## CLI calibration

Semantic evaluation is available only on a single `run` and is explicitly opt-in:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --semantic-claims \
  --json
```

`--semantic-claims` implies deterministic `--claims`; both deterministic and merged semantic results are returned.

A semantic-stage provider, rate-limit, or schema-validation failure returns exit code `2` while preserving the successful original pattern run in the immediate output.

## Privacy and artifact boundary

The semantic layer processes claim text and evidence summaries, so it remains outside metadata-only artifacts.

It does **not** modify:

- metadata-only execution traces;
- `runs.jsonl` benchmark records;
- `summary.csv`;
- `summary.md`;
- the historical 60-run experiment dataset.

The trace is recorded from `PatternRun` before claim/semantic analysis and continues to exclude model answers, claim text, evidence bodies, tool arguments/results, and credentials.

## Calibration mode and self-judge bias

The current CLI reuses the already selected provider/model as the semantic `TextModel`. This is intentional for a small v2.1 calibration slice, but it is **not an independent judge** when the same model generated the answer.

That creates a methodological risk: a model may be biased toward accepting its own wording or reasoning. Therefore:

- v2.1 semantic results are calibration evidence, not ground truth;
- semantic support must not be presented as an independent quality score;
- semantic metrics are not enabled in repeated benchmarks;
- deterministic hard failures remain authoritative;
- disagreements stay observable.

A stronger later phase should decouple generation from evaluation, for example with a separately configured evaluator provider/model and cross-model calibration against static fixtures.

## Live calibration results

Two live OpenAI `gpt-5.6-luna` bounded-agent runs were used to calibrate the v2.1 contract. Both preserved 100% Grounding v1 specific grounding, had no unsupported specifics or causality overclaims, respected the strict semantic JSON contract, and exited successfully.

### First smoke — before deterministic refinement

The generated answer produced three conservative deterministic misses. The semantic layer upgraded all three correctly:

1. deployment included a new payment-provider timeout configuration;
2. no confirmed payment-provider outage;
3. prior incident involved an upstream timeout mismatch and was historical context.

Observed semantic usage:

- semantic model calls: `3`;
- semantic input tokens: `1161`;
- semantic output tokens: `174`;
- disagreements: `3`;
- merged support ratio: `1.0`.

The first two upgrades were unnecessary LLM work because those facts were already near-verbatim in bounded current-incident evidence. That observation motivated the deterministic pre-filter refinement above.

### Second smoke — after deterministic refinement

A newly generated answer was evaluated after the refinement. Because the answer text changed between runs, raw claim counts are not treated as a paired before/after quality comparison. The second smoke is used only to validate routing/selectivity of the evaluation layers.

Deterministic v2 classified:

- 4 supported facts;
- 3 supported inferences;
- 4 proposed actions;
- 1 unsupported claim;
- support ratio `7/8` (`87.5%`).

The only unsupported claim was the historical paraphrase:

> A prior incident had similar symptoms involving an upstream timeout mismatch, but that is historical context only.

The semantic evaluator received only that claim, returned `SUPPORTED_FACT` using `previous-incidents`, and produced:

- semantic model calls: `1`;
- semantic input tokens: `394`;
- semantic output tokens: `93`;
- disagreements: `1`;
- final supported facts: `5`;
- final supported inferences: `3`;
- final proposed actions: `4`;
- final unsupported claims: `0`;
- merged support ratio: `1.0`.

This validates the intended execution policy for v2.1: deterministic checks resolve exact and high-confidence bounded facts, Grounding v1 hard failures remain fail-closed, and semantic evaluation is invoked only for conservative misses that require actual entailment.

## Interpretation boundary

The live results validate implementation behavior, not semantic-evaluator accuracy in general. In particular:

- the same model generated and judged the answer;
- the fixture contains one incident and one semantic calibration class;
- two live runs are insufficient for statistical conclusions;
- a `1.0` merged support ratio is not proof that the full answer is universally correct;
- semantic upgrades are not part of the repeated cross-provider benchmark dataset.

The strongest supported conclusion is architectural: the evaluator can preserve deterministic authority while selectively escalating ambiguous claims and keeping that extra model cost separately observable.

## Not in v2.1

This phase deliberately does not add:

- an independent evaluator provider/model configuration;
- semantic metrics to repeated benchmarks;
- semantic claim text to metadata artifacts;
- NLI or embedding dependencies;
- provider-specific structured-output APIs;
- retries for malformed evaluator output;
- a mechanism for semantic judgement to override Grounding v1 hard failures.

Those are separate design decisions. The next meaningful evaluation step is to decouple generation from semantic judgement and calibrate cross-model disagreement against static fixtures.