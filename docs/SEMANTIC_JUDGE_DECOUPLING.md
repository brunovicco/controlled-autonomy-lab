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

## First intended cross-model smoke

Use the already-calibrated OpenAI generator with Groq GPT-OSS as the judge:

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

For an answer similar to the v2.1 calibration fixture, the expected routing behavior is one semantic call for the historical incident paraphrase. The semantic verdict itself is **not** predetermined. If GPT-OSS keeps it unsupported while the previous OpenAI self-judge upgraded it, that disagreement is useful evidence rather than a failure to hide.

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
- any mechanism that overrides Grounding v1 hard failures.

A later phase can add a static labelled claim set and run a generator × judge matrix to measure agreement, false upgrades, false rejections, and cross-model bias without consuming fresh architecture runs.
