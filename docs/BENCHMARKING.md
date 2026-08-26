# Reproducible Benchmark v1

Reproducible Benchmark v1 turns the six architecture patterns into a repeatable experiment over the same incident fixture.

The benchmark is intended to answer practical questions such as:

- how many model/tool calls each architecture requires;
- how token use and latency change as control shifts toward the model;
- whether higher autonomy improves or degrades deterministic grounding;
- how often provider rate limits or other provider failures prevent completion;
- whether agent trajectories vary across repeated runs.

It does not claim that one provider/model result generalizes to every model or production workload.

## Run a benchmark

```bash
uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --output results/groq-gpt-oss-20b \
  --run-interval-seconds 30
```

The command executes all six patterns once per cycle. The starting pattern rotates deterministically on each cycle so the same architecture is not always first or last:

```text
cycle 1: augmented -> chaining -> routing -> parallel -> evaluator-optimizer -> agent
cycle 2: chaining -> routing -> parallel -> evaluator-optimizer -> agent -> augmented
cycle 3: routing -> parallel -> evaluator-optimizer -> agent -> augmented -> chaining
...
```

This reduces fixed-order exposure to quota drift while keeping the experiment deterministic and reproducible.

## Pacing semantics

`--run-interval-seconds` inserts a pause **between benchmark attempts**.

It deliberately does not throttle calls inside an architecture pattern. Therefore:

- `parallel` keeps its concurrent fan-out;
- `chaining` keeps its sequential internal calls;
- evaluator-optimizer keeps its bounded revision loop;
- the agent keeps its dynamic tool/model loop.

This preserves the behavior being measured. A provider `429` that occurs inside a pattern remains benchmark evidence rather than being hidden by an implicit retry or a benchmark-specific serialization layer.

There are no automatic retries in Benchmark v1.

### Groq Free Plan calibration

Two live smoke benchmarks were run on 2026-08-26 with `openai/gpt-oss-20b` and `LLM_MAX_TOKENS=900`:

| Interval | Completed patterns | Result |
| --- | ---: | --- |
| `2s` | `2/6` | `augmented` and `chaining` completed; the remaining four patterns were rate-limited |
| `30s` | `6/6` | all six patterns completed; benchmark exit code `0` |

The 30-second smoke completed with these single-run grounding ratios: augmented `78.6%`, chaining `20.0%`, routing `84.6%`, parallel `85.7%`, evaluator-optimizer `91.7%`, and agent `78.6%`. These are calibration observations with `n=1`, not comparative conclusions; repeated cycles are required before interpreting architecture-level quality differences.

As of 2026-08-26, Groq's public Free Plan table lists `openai/gpt-oss-20b` at 30 RPM, 1K RPD, 8K TPM, and 200K TPD. Groq also states that rate limits apply at the organization level, that any configured limit can trigger first, and that the account Limits page is the source of truth for exact organization-specific values.

For this repository's six-pattern workload, **30 seconds between benchmark attempts is the recommended conservative starting point for Groq Free Plan experiments**. It is a benchmark configuration, not an automatic retry or guarantee. If the organization-specific limit differs or `429` still occurs, preserve that run as evidence and execute a separate experiment with a larger interval.

Do not rerun only failed patterns and splice them into the original benchmark. That would change the experimental conditions and distort reliability metrics.

Official reference:

- Groq rate limits: https://console.groq.com/docs/rate-limits

## Output protection

The benchmark writes three canonical files into the selected output directory:

```text
results/groq-gpt-oss-20b/
├── runs.jsonl
├── summary.csv
└── summary.md
```

Existing canonical files are not overwritten by default. Use `--overwrite` only when replacement is intentional:

```bash
uv run autonomy-lab benchmark \
  --runs 5 \
  --output results/groq-gpt-oss-20b \
  --overwrite
```

The existence check happens before live pattern execution so an accidental overwrite does not consume provider quota first.

## Raw record schema

`runs.jsonl` contains one metadata-only record for every attempted pattern execution.

Successful records include:

```text
timestamp_utc
git_commit
provider
model
max_tokens
timeout_seconds
reasoning_effort
run_interval_seconds
incident_id
pattern
run_number
status
model_calls
tool_calls
input_tokens
output_tokens
latency_ms
unsupported_count
proposed_count
causality_overclaims
grounding_ratio
uncertainty_preserved
trajectory
```

Failure records preserve the experiment position and provider outcome. A rate-limited row can also contain a safe `retry_after` value when the provider supplied it.

The `error` field contains the redacted provider error already enforced by the provider boundary; provider response bodies are not copied into benchmark artifacts.

## Metadata-only boundary

Benchmark artifacts do **not** persist:

- prompts;
- model answers;
- evidence bodies;
- tool arguments or tool results;
- credentials.

Grounding is evaluated while the answer exists in process memory, but only aggregate deterministic grounding metrics are persisted.

The existing global `--trace-file` option remains compatible with successful benchmark runs and retains its original metadata-only contract.

## Summary metrics

`summary.csv` and `summary.md` aggregate each architecture independently.

Reliability metrics use **all attempted runs**:

- `completion_rate`;
- `rate_limit_rate`;
- `provider_error_rate`.

Execution and grounding averages use **completed runs only**. Failed attempts are not assigned zero calls, zero tokens, zero latency, or zero grounding because doing so would fabricate measurements.

Current aggregates include:

- mean model calls;
- mean tool calls;
- mean input/output/total tokens;
- p50 latency;
- mean unsupported factual findings;
- mean proposed parameters;
- mean causality overclaims;
- mean specific-grounding ratio;
- uncertainty-preservation rate;
- unique successful trajectories.

When at least one attempt is rate-limited, `summary.md` explicitly states that the rate limit is benchmark evidence and recommends using a larger interval only in a **separate** experiment.

## Exit codes

A complete benchmark returns:

```text
0
```

If at least one attempted pattern is `rate_limited` or has another provider failure, all remaining attempts still run and the benchmark returns:

```text
2
```

This matches the fail-soft behavior of `compare`.

## Reproducibility metadata

The Git commit is discovered without invoking a shell. Resolution order is:

1. `AUTONOMY_LAB_GIT_COMMIT`;
2. `GITHUB_SHA`;
3. the local `.git/HEAD` reference, including packed refs;
4. `unknown` when no repository metadata is available.

Provider credentials are never part of the recorded environment.

For Groq `openai/gpt-oss-20b` and `openai/gpt-oss-120b`, Benchmark v1 records `reasoning_effort=medium` because Groq currently documents `medium` as the provider default for those models. The runtime does not yet expose a generic reasoning-effort override, so Benchmark v1 does not record an environment variable that the transport would ignore.

Official references:

- Groq API reference: https://console.groq.com/docs/api-reference
- Groq GPT-OSS 20B: https://console.groq.com/docs/model/openai/gpt-oss-20b
- Groq rate limits: https://console.groq.com/docs/rate-limits

## Recommended experiment protocol

For a first publishable local experiment:

1. choose one provider/model and freeze the environment variables;
2. sync the repository and record the exact commit automatically;
3. choose a dedicated output directory;
4. choose pacing appropriate to the provider/account limits;
5. run at least five cycles;
6. preserve partial results instead of rerunning only failed patterns;
7. treat rate-limit rate as part of the observed provider/runtime behavior;
8. compare another provider/model in a separate output directory rather than mixing configurations.

Groq Free Plan example:

```bash
export LLM_PROVIDER=groq
export GROQ_MODEL=openai/gpt-oss-20b
export LLM_MAX_TOKENS=900

uv run autonomy-lab benchmark \
  --incident INC-001 \
  --runs 5 \
  --run-interval-seconds 30 \
  --output results/groq-gpt-oss-20b-900
```

## Known limitations

Benchmark v1 intentionally remains narrow:

- one incident fixture is not a universal workload benchmark;
- deterministic grounding v1 only checks its documented factual structures;
- model/provider conditions and rate limits can change over time;
- the documented Groq Free Plan baseline is a dated experimental recommendation, not a permanent provider guarantee;
- cost is not normalized because providers expose different pricing and free-tier behavior;
- no hidden retry means transient failures remain visible rather than being corrected after the fact;
- p50 latency summarizes completed runs but does not characterize tail latency with small sample sizes;
- reasoning-effort metadata is only populated when the effective runtime setting is known.

The benchmark is evidence for architectural trade-offs, not proof that one pattern or provider is universally superior.
