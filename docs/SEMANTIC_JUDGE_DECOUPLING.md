# Semantic Judge Decoupling v2.2

Semantic Judge Decoupling v2.2 separates answer generation from semantic claim judgement without changing the deterministic authority model introduced in v2.1.

The goal is not to create a new benchmark score. It is to make generator-versus-judge disagreement observable while preserving Grounding v1 hard failures and keeping semantic post-analysis outside metadata-only benchmark artifacts.

## Why decouple the judge

v2.1 proved that selective semantic escalation can resolve conservative deterministic misses, but its live calibration used the same OpenAI model to generate and judge the answer. That creates self-judge bias: the model may be more likely to accept its own wording or reasoning.

v2.2 allows a different provider/model to judge the generated answer so that the system can observe:

```text
generator result
      ↓
deterministic evaluation
      ↓
eligible conservative miss
      ↓
independent semantic judge
      ↓
merged result + disagreement
```

This is still calibration, not ground truth. A second model can disagree for good or bad reasons.

## Authority invariant

The v2.1 authority model does not change:

```text
Grounding v1 hard failure
        ↓
semantic evaluation skipped
        ↓
UNSUPPORTED_CLAIM remains authoritative
```

The semantic judge may only evaluate conservative deterministic misses that are already eligible under v2.1. It cannot:

- override unsupported measurements, versions, associations, or causal hard failures;
- downgrade deterministic support;
- reclassify proposed actions;
- add claims or semantic text to metadata-only benchmark artifacts.

## Provider configuration

Generator settings continue to use the existing variables:

```text
LLM_PROVIDER
LLM_MAX_TOKENS
LLM_TIMEOUT_SECONDS
<provider model/key variables>
```

The semantic judge can override them with the `SEMANTIC_` namespace:

```text
SEMANTIC_LLM_PROVIDER
SEMANTIC_LLM_MAX_TOKENS
SEMANTIC_LLM_TIMEOUT_SECONDS
SEMANTIC_OPENAI_MODEL
SEMANTIC_GROQ_MODEL
SEMANTIC_CLAUDE_MODEL
SEMANTIC_OPENROUTER_MODEL
```

Provider credentials can also be namespaced, for example `SEMANTIC_GROQ_API_KEY`. A namespaced credential is optional: if omitted, the judge falls back to the existing provider-specific key such as `GROQ_API_KEY`.

If no `SEMANTIC_*` overrides are supplied, v2.2 preserves the v2.1 behavior and reuses the generator provider/model. The calibration output marks this explicitly as `self_judge: true`.

No API key is included in `ProviderSelection`, calibration output, or metadata traces.

## Cross-model calibration command

The decoupled calibration surface is intentionally separate from `autonomy-lab benchmark`:

```bash
uv run python -m autonomy_lab.semantic_judge_cli agent \
  --incident INC-001 \
  --json
```

The command executes one pattern with the generator, then runs Grounding v1, deterministic Claim Evaluation v2, and the v2.1 semantic merge using the separately configured judge.

The JSON output includes non-secret identities:

```json
{
  "generator": {
    "provider": "openai",
    "model": "gpt-5.6-luna",
    "max_tokens": 4000,
    "timeout_seconds": 60.0
  },
  "judge": {
    "provider": "groq",
    "model": "openai/gpt-oss-20b",
    "max_tokens": 600,
    "timeout_seconds": 30.0
  },
  "self_judge": false
}
```

Pattern `model_calls`, token usage, latency, and trajectory remain the generator execution metrics. Semantic calls and tokens stay under `semantic_claim_evaluation` and are not added to the pattern's execution totals.

## Failure behavior

Generator failures retain the existing provider/rate-limit behavior.

Judge failures are post-run analysis failures. The successful generator answer is preserved and the command returns exit code `2` when the judge has:

- invalid/missing configuration;
- a provider error;
- a rate limit;
- malformed or unbounded semantic JSON.

A judge failure is not converted into a claim verdict.

## Cross-model smoke

The first live cross-model calibration used:

- generator: OpenAI `gpt-5.6-luna`;
- judge: Groq `openai/gpt-oss-20b`;
- generator max output tokens: `4000`;
- judge max output tokens: `600`;
- `self_judge: false`.

The bounded agent completed successfully with the expected six-step trajectory, five tool calls, and two generator model calls. Grounding v1 reported 100% specific grounding, zero unsupported specifics, zero proposed specifics, zero causality overclaims, and preserved uncertainty.

The deterministic evaluator left the historical incident paraphrase as the only ordinary conservative semantic candidate. GPT-OSS judged that claim as `SUPPORTED_FACT` using `previous-incidents`, producing one semantic disagreement and one semantic upgrade. Semantic usage remained separate from generation:

- semantic model calls: `1`;
- semantic input tokens: `458`;
- semantic output tokens: `254`.

This confirms the main v2.2 infrastructure goal: generation and semantic judgement can use different providers/models, judge identity is explicit, self-judging is disabled, and semantic cost remains independently observable.

### Calibration bug exposed by the first smoke

The same run also exposed an evaluator inconsistency unrelated to the Groq judge. The answer stated that the available evidence **does not prove** that the deployment caused the incident. Whole-answer Grounding v1 correctly reported zero causal overclaims, but sentence-level Claim Evaluation initially re-ran Grounding v1 on that sentence and marked it as `grounding-v1-causality-overclaim:1`.

The cause was granularity-sensitive uncertainty detection: whole-answer Grounding saw the surrounding `leading hypothesis` qualifier on the same paragraph line, while the claim evaluator split the paragraph into sentences. The uncertainty vocabulary recognized `not proven` but not the equally explicit form `does not prove`.

The deterministic claim evaluator now includes a narrow explicit causal-uncertainty rule for forms such as `not prove`, `not proved`, `not proven`, `cannot prove`, and `can't prove`. Those forms:

- prevent a false sentence-level causality hard failure;
- qualify the claim as an inference when evidence anchors exist;
- do **not** weaken the existing fail-closed behavior for unqualified language such as `The deployment caused the incident.`

A regression test freezes the exact causal sentence observed in the first cross-model smoke. The corrected deterministic classification is `SUPPORTED_INFERENCE` with deployment/dependency evidence anchors, while the original unqualified causal-overclaim test remains fail-closed.

## Second cross-model smoke

A second live run repeated the same provider split after the sentence-level causal-uncertainty fix:

- generator: OpenAI `gpt-5.6-luna`;
- judge: Groq `openai/gpt-oss-20b`;
- `self_judge: false`;
- generator model calls: `2`;
- tool calls: `5`;
- semantic model calls: `1`;
- semantic input tokens: `458`;
- semantic output tokens: `306`;
- semantic disagreements: `1`;
- final semantic support ratio: `1.0`.

The historical incident paraphrase again remained the only ordinary conservative semantic candidate and GPT-OSS again upgraded it to `SUPPORTED_FACT` using `previous-incidents`. This is useful repeated calibration evidence for the decoupled routing path, but it is still not a judge-accuracy estimate.

### Causal-rejection false positive exposed by the second smoke

The second answer contained the recommendation:

```text
Avoid treating the historical incident as confirmation of the current root cause.
```

Grounding v1 initially matched `root cause` and reported a causality overclaim even though the sentence explicitly rejects that conclusion. Claim Evaluation correctly treated the sentence as a proposed action, which made the mismatch visible.

Grounding v1 now recognizes a deliberately narrow set of explicit causal-rejection forms, including `avoid treating`, `avoid assuming`, `do not treat`, `do not assume`, `never claim`, and related bounded variants. This prevents advisory language that rejects a causal conclusion from being counted as the conclusion itself.

The correction does **not** suppress causality checks merely because text appears under a recommendation heading. An unqualified statement such as:

```text
The deployment is the root cause of the incident.
```

continues to produce a causality overclaim. Both the observed rejection sentence and the unqualified control are frozen as regression tests.

The project quality gate after this correction passes with 122 tests plus Ruff lint/format, architecture validation, strict MyPy, Bandit, and pip-audit.

No additional provider call is required to validate this second deterministic correction: both OpenAI→Groq live smokes already validated the decoupled transport/routing behavior, while the correction itself is deterministic and regression-tested.

## Reproduction

```bash
set -a
source .env
set +a

export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-5.6-luna
export LLM_MAX_TOKENS=4000
export LLM_TIMEOUT_SECONDS=60

export SEMANTIC_LLM_PROVIDER=groq
export SEMANTIC_GROQ_MODEL=openai/gpt-oss-20b
export SEMANTIC_LLM_MAX_TOKENS=600
export SEMANTIC_LLM_TIMEOUT_SECONDS=30

uv run python -m autonomy_lab.semantic_judge_cli agent \
  --incident INC-001 \
  --json

echo $?
```

If `GROQ_API_KEY` is already loaded, a separate `SEMANTIC_GROQ_API_KEY` is not required.

The semantic verdict is deliberately not predetermined for future answers. Agreement or disagreement between generator-side deterministic evaluation and an independent judge is calibration evidence rather than a success criterion by itself.

## Interpretation boundary

A single generator/judge pair on one incident cannot establish evaluator accuracy. In particular:

- neither model is ground truth;
- one semantic class is insufficient to estimate judge precision or recall;
- judge model size, transport, reasoning behavior, and output budget differ;
- a cross-model agreement can still be jointly wrong;
- a disagreement requires inspection against static human-labelled fixtures.

The strongest purpose of v2.2 is therefore architectural and methodological: make judge identity explicit, separate its cost from generation, remove implicit self-judging, and expose disagreement for later calibration.

## Not in v2.2

This phase deliberately does not add:

- semantic metrics to repeated architecture benchmarks;
- a model-as-judge leaderboard;
- automatic consensus across multiple judges;
- retries for judge failures;
- semantic claim text to metadata-only traces;
- any mechanism that overrides genuine Grounding v1 hard failures.

A later phase can add a static labelled claim set and run a generator × judge matrix to measure agreement, false upgrades, false rejections, and cross-model bias without consuming fresh architecture runs.
