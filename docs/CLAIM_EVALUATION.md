# Claim Evaluation v2

Claim Evaluation v2 adds a claim-level view on top of the existing deterministic Grounding v1 checks.

It does **not** replace Grounding v1. The two layers answer different questions:

- **Grounding v1:** are exact factual specifics, associations and strong causal statements supported by the bounded fixture?
- **Claim Evaluation v2:** what role does each evaluable statement play: supported fact, qualified inference, proposed action, or unsupported claim?

The first v2 implementation is intentionally conservative and deterministic. It does not call another model and does not claim to provide general semantic entailment.

## Taxonomy

| Kind | Meaning |
| --- | --- |
| `SUPPORTED_FACT` | A declarative claim has deterministic fixture support and no hard Grounding v1 failure. |
| `SUPPORTED_INFERENCE` | A qualified inference/hypothesis is anchored to bounded evidence and has no hard Grounding v1 failure. |
| `PROPOSED_ACTION` | The statement is a recommendation, check, mitigation or other future action rather than an observed fact. |
| `UNSUPPORTED_CLAIM` | The deterministic baseline cannot support the claim, or Grounding v1 reports an unsupported specific or causal overclaim. |

Every extracted claim receives exactly one of these classifications.

## Precedence

Classification is deliberately asymmetric:

1. Detect proposal/action context. Under a recommendation/action heading, list items are treated as section actions; imperative statements can also be actions outside a list.
2. Run Grounding v1 hard checks for non-proposals.
3. If Grounding v1 reports an unsupported specific, classify `UNSUPPORTED_CLAIM`.
4. If Grounding v1 reports a causality overclaim, classify `UNSUPPORTED_CLAIM`.
5. Recognize a qualified inference only when it has a bounded evidence-source anchor.
6. Recognize a fact when deterministic fixture support exists.
7. Otherwise fail closed to `UNSUPPORTED_CLAIM`.

This ordering matters. A recommendation such as `Monitor for 15 minutes` may introduce a new parameter legitimately; it should not be treated as an observed 15-minute fact. Conversely, a semantic evaluator added later must not be allowed to erase a deterministic unsupported version, measurement or causality finding.

The action-heading rule is intentionally bounded. A free-standing declarative conclusion after a numbered recommendation list does not inherit `PROPOSED_ACTION` merely because the most recent heading was a recommendation heading.

## Claim extraction

The baseline extracts non-empty sentence-like statements while retaining the current Markdown section heading. Markdown headings and bold-only headings are not themselves treated as claims. Bullet and numbered-list prefixes are removed before evaluation, while the extractor retains whether the original statement was a list item.

Section context is used to distinguish areas such as:

- observed facts;
- hypotheses / assessment;
- recommendations / next steps / actions / mitigation.

The extractor is intentionally small and deterministic. It is not a general-purpose discourse parser.

## Evidence anchors

For the deterministic baseline, a supported inference must:

- contain explicit inference/uncertainty language or appear in a hypothesis/assessment section; and
- overlap with at least one bounded evidence source.

This evidence anchor is a calibration heuristic, not semantic entailment. It prevents an unrelated statement such as `A memory leak might explain the incident` from being upgraded merely because it uses cautious language.

`evidence_sources` should be read as **candidate lexical anchors**, not exact provenance. The current overlap heuristic can over-attribute a claim to multiple sources when shared vocabulary appears across the fixture. Tightening provenance is a separate calibration problem because the same anchors participate in inference support; an ad-hoc source filter can otherwise turn valid qualified inferences into false negatives.

## Explicit uncertainty and causal language

Grounding v1 treats explicit epistemic negation such as `no confirmed`, `not confirmed`, `unconfirmed`, and `no evidence` as uncertainty signals. Therefore a sentence such as `No confirmed root cause is currently available` is not a causality overclaim merely because it contains the lexical phrase `root cause`.

This is distinct from a strong unqualified causal statement such as `The deployment caused the incident`, which remains a hard Grounding v1 failure.

## Support ratio

`support_ratio` is:

```text
supported facts + supported inferences
--------------------------------------
     evaluable non-action claims
```

Proposed actions are visible but excluded from the denominator.

If an answer contains only proposed actions, the ratio is `1.0` by convention, mirroring the existing Grounding v1 empty-denominator behavior. The count fields remain necessary context; the ratio should never be interpreted alone.

## Relationship to Grounding v1

The v2 deterministic evaluator composes the existing `DeterministicGroundingEvaluator` rather than duplicating its exact-specific logic.

Hard-signal invariant:

```text
Grounding v1 unsupported specific
            OR
Grounding v1 causality overclaim
            ↓
Claim v2 = UNSUPPORTED_CLAIM
```

A future semantic evaluator may improve coverage for paraphrases and nuanced inferences, but it must not override that invariant.

## CLI calibration

Claim Evaluation v2 is initially exposed only for single runs:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims
```

JSON output:

```bash
uv run autonomy-lab run agent \
  --incident INC-001 \
  --grounding \
  --claims \
  --json
```

The JSON response includes a `claim_evaluation` object with per-claim classifications plus aggregate counts and `support_ratio`.

The `--claims` flag is opt-in. Benchmark schemas and historical experiment artifacts are unchanged in this phase.

## Observed-run regression fixture

The repository includes a static answer captured from a successful OpenAI `gpt-5.6-luna` bounded-agent run for `INC-001` under `tests/fixtures/observed/`.

Only the answer text is retained. The fixture excludes prompts, credentials, latency, token accounting, tool arguments/results, and provider request/response payloads.

The regression currently freezes these deterministic expectations:

- Grounding v1: no unsupported specifics and no causal overclaim for explicit negative causal language;
- Claim v2: 4 supported facts, 4 supported inferences, 4 proposed actions, and 1 conservative unsupported paraphrase;
- the historical-incident paraphrase remains unsupported in the deterministic layer by design until a semantic evaluator is calibrated;
- the free-standing conclusion after the recommendation list is an epistemically qualified inference, not a proposed action.

This fixture lets claim semantics evolve without consuming provider quota in unit tests.

## Metadata and privacy boundary

Per-claim output contains answer text fragments, so it is **not** written to metadata-only traces or benchmark artifacts.

The existing metadata boundary remains unchanged:

- no prompts;
- no model answers;
- no claim text;
- no evidence bodies;
- no tool arguments/results;
- no credentials.

Claim evaluation is displayed only in the immediate CLI response when explicitly requested.

## Known limitations

The deterministic baseline is deliberately conservative:

- lexical evidence overlap is not NLI;
- evidence-source anchors may over-attribute provenance when vocabulary is shared across sources;
- paraphrases without exact/specific support may remain `UNSUPPORTED_CLAIM`;
- sentence splitting is intentionally narrow;
- discourse context across multiple sentences is limited;
- evidence-source overlap does not prove an inference is logically valid;
- one incident fixture is not enough to calibrate general claim semantics;
- `support_ratio` is not a universal answer-quality score.

These limitations are preferable to silently presenting heuristic semantic judgments as ground truth.

## Planned semantic layer

A later semantic evaluator should be a **secondary** signal. The intended merge policy is:

1. deterministic hard failure always wins;
2. proposed actions remain separate from factual support;
3. semantic evaluation may distinguish supported paraphrases from unsupported declarative claims;
4. semantic evaluation may refine qualified inference support;
5. disagreements between deterministic and semantic evaluators remain observable rather than being silently collapsed.

Before enabling semantic claim metrics in repeated benchmarks, calibrate the evaluator against static observed-run fixtures so provider quota is not required for unit tests.
