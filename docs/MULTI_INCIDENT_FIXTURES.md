# Multi-Incident Fixture Suite

Controlled Autonomy Lab originally used one deliberately ambiguous fixture, `INC-001`, to compare six autonomy patterns under a fixed evidence boundary. Phase 3C adds three contrasting fixtures so the lab can test whether architecture and evaluator behavior generalize across different causal postures.

## Design goal

The experiment should vary **what the evidence actually proves** without changing the application boundary available to each architecture.

Every incident therefore exposes exactly five evidence categories:

1. `metrics`
2. `deployments`
3. `dependencies`
4. `runbook`
5. `previous-incidents`

The bounded agent receives the same five read-only tools for every fixture. Workflow patterns receive the same complete evidence tuple. No incident gets an extra privileged tool or hidden evidence source.

## Scenario matrix

| Incident | Service | Evidence posture | Expected causal behavior |
| --- | --- | --- | --- |
| `INC-001` | `checkout-api` | deployment timing and dependency latency are correlated | preserve uncertainty; current cause is not proven |
| `INC-002` | `checkout-api` | rollback + controlled replay explicitly confirm a release regression | deployment cause may be stated as confirmed when causal details match evidence |
| `INC-003` | `payments-api` | provider incident explicitly confirms an upstream regional outage | dependency cause may be stated as confirmed when causal details match evidence |
| `INC-004` | `profile-api` | local and dependency signals are insufficient and partially conflicting | abstain from root-cause attribution and request missing evidence |

These fixtures are synthetic and deterministic. They exist to exercise epistemic behavior, not to model every production-incident failure mode.

## Confirmed-causality contract

Grounding Evaluation v1 historically treated unqualified current-incident causality as an overclaim because `INC-001` contains correlation without proof.

That rule cannot represent a fixture where evidence genuinely confirms a cause. Phase 3C therefore adds one narrow positive path.

Current causal language is accepted only when:

1. the bounded fixture explicitly contains `Root cause confirmed for INC-xxx` for the active incident;
2. that confirmation itself is not uncertainty/rejection language; and
3. the model claim shares at least two material causal-detail tokens with the confirmed evidence.

Examples:

```text
INC-002
The v2.19.1 800ms timeout regression caused the checkout errors.
→ supported causal statement

The payment-provider outage caused INC-002.
→ causal overclaim
```

```text
INC-003
The payment-provider regional outage caused the downstream 503 errors.
→ supported causal statement

A payments-api deployment caused INC-003.
→ causal overclaim
```

```text
INC-004
The identity-provider latency caused INC-004.
→ causal overclaim

Root cause remains unconfirmed for INC-004; more evidence is needed.
→ uncertainty preserved
```

The evaluator does **not** infer confirmed causality from timing, rollback alone, recovery ordering, historical similarity, or generic use of the word `confirmed`.

## Why this matters

A grounding evaluator that only penalizes causal claims can look safe on an ambiguity-only dataset while being unable to recognize when strong evidence justifies a causal conclusion.

The multi-incident suite creates both sides of the calibration problem:

```text
unsupported causal assertion
        ↓
must fail closed

explicitly evidenced causal conclusion
        ↓
must not be penalized merely for being causal
```

The goal is calibrated epistemic behavior, not universal abstention.

## Live smoke and deterministic replay calibration

Three live `claude-sonnet-5` bounded-agent smokes were run against `INC-002`, `INC-003`, and `INC-004` before merge.

All three used the same topology:

- 2 generator model calls;
- 5 read-only tool calls;
- all five evidence tools before the final answer.

At the architecture level the expected epistemic posture was observed:

- `INC-002` concluded the confirmed deployment/timeout regression cause;
- `INC-003` identified the confirmed payment-provider incident while preserving a caveat about independent raw-log verification;
- `INC-004` explicitly abstained from a root-cause conclusion and requested additional evidence.

The original live outputs then became fixed replay inputs for the deterministic evaluators. Replaying identical text avoids provider variance and consumes no additional API quota.

Smoke-derived regressions now cover:

- HTTP status plurals such as `503s` so they are not parsed as `503 seconds`;
- spelled-out fixture durations and equivalent numeric paraphrases;
- timeline association extraction across evidence/newline boundaries;
- locally explicit Markdown timeline relationships;
- runbook methodology statements that mention causal standards without asserting a new current cause;
- explicit causal meta/rejection language;
- reported-cause attribution;
- explicit abstention language, including inline Markdown emphasis;
- Markdown table structure and discourse labels that should not become claims;
- narrow exclusion inferences anchored to explicit negative fixture evidence;
- action-oriented statements that should remain proposed actions rather than observed facts.

The claim replay deliberately retains two conservative `INC-004` misses:

1. a faithful historical paraphrase of `INC-655`, which remains a good semantic-escalation candidate;
2. `Could be a partial trigger or coincidental.`, which depends on sentence-to-sentence context that Claim Evaluation v2 does not currently propagate.

The calibration objective is therefore **not** to force a `100%` claim-support ratio. It is to remove deterministic evaluator noise without weakening the authority boundary or pretending to solve contextual entailment lexically.

The final regression suite contains **167 tests** and the phase head `3d410c92748c98c7bf56f482df60c3bb6e2b175e` passed Ruff lint/format, strict MyPy, architecture validation, Bandit, pip-audit, and the project coverage threshold.

## Frozen benchmark boundary

The existing 90-run OpenAI/Groq/Anthropic architecture benchmark remains frozen on:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

and uses only `INC-001`.

Those results remain historical evidence for the original experiment. They are not reclassified after Phase 3C.

A future multi-incident benchmark must use a **new frozen commit after these fixtures merge** and report itself as a separate experiment generation. This is necessary because the fixture set and Grounding v1 causal-support semantics have changed.

## Recommended live calibration sequence

Before launching a large repeated matrix:

1. run one smoke per new incident with a single provider;
2. inspect the model answer plus Grounding/Claim Evaluation for causal posture;
3. freeze any evaluator bugs as deterministic regressions;
4. replay the exact saved answers through the corrected evaluators;
5. only then run multi-incident architecture experiments.

The first architecture experiment should favor breadth over repetition:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 executions
```

This gives cross-scenario coverage before spending quota on `n=5` repetitions. If the scenario-level behavior is coherent, a selected repeated matrix can then be frozen for statistical comparison.

## Non-goals

This phase does not:

- modify or reinterpret the frozen 90-run benchmark;
- add semantic/NLI causal inference;
- change agent tool permissions;
- introduce production writes;
- add MCP or A2A without a real process boundary;
- claim that four synthetic incidents establish broad external validity.
