# Multi-Incident Breadth Benchmark

Phase 3D adds a breadth-first benchmark mode on top of the existing reproducible benchmark runner.

The experiment has now been executed and reported as a distinct frozen generation.

## Experiment shape

The main breadth generation intentionally uses one run per incident/pattern/provider bundle:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

The experiment asks whether architecture-level behavior observed on `INC-001` persists when the evidence posture changes.

It is not a replacement for the frozen 90-run repeated benchmark. The two experiments answer different questions:

- the **90-run repeated benchmark** exposes repeated behavior and within-fixture trajectory variation;
- the **72-cell breadth benchmark** exposes behavior across different causal and evidentiary postures.

## Canonical incidents

- `INC-001`: correlation without proven current cause;
- `INC-002`: deployment cause explicitly confirmed;
- `INC-003`: dependency cause explicitly confirmed;
- `INC-004`: inconclusive incident requiring abstention.

## Frozen generation

Main breadth implementation freeze:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

The generation contains:

```text
72 attempted cells
59 successful cells
12 rate-limited cells
1 provider-error cell
```

Provider availability:

| Provider | Successful | Attempted | Completion |
| --- | ---: | ---: | ---: |
| OpenAI | 24 | 24 | 100.0% |
| Groq | 12 | 24 | 50.0% |
| Anthropic | 23 | 24 | 95.8% |

Groq rate limits affected every pattern in `INC-003` and `INC-004`. Those cells are availability evidence, not quality zeros.

The Anthropic `INC-003/chaining` cell ended in a provider error and is likewise excluded from quality aggregation.

## Architecture-level observed results

Quality metrics are calculated only on successful (`status=ok`) cells.

| Pattern | Observed | Mean grounding | Causal overclaims |
| --- | ---: | ---: | ---: |
| Augmented | 10/12 | 97.8% | 3 |
| Chaining | 9/12 | 74.4% | 5 |
| Routing | 10/12 | 92.8% | 2 |
| Parallel | 10/12 | 94.9% | 7 |
| Evaluator-optimizer | 10/12 | 97.6% | 4 |
| Agent | 10/12 | 95.4% | **0** |

These results are descriptive because the experiment uses `n=1` per cell. They do not establish statistical significance or universal architecture rankings.

## Strongest observations

- bounded tool-using agency was the only pattern with zero detected causal overclaims across all observable breadth cells;
- chaining showed the weakest aggregate grounding and a poor cost/latency trade-off;
- parallelization preserved relatively high grounding while producing the largest number of causal overclaims;
- evaluator-optimizer exhibited adaptive revision behavior, but internal quality passes did not guarantee external causal correctness;
- routing exposed provider/model-dependent control-flow selection;
- grounding and causal authority remained distinct evaluation dimensions;
- lexical uncertainty-language detection saturated across successful cells and is not interpreted as epistemic correctness.

The result should not be summarized as “agents are better.”

The narrower supported hypothesis is that bounded tool use may help evidence acquisition and causal restraint when the agent operates inside explicit read-only tool, action, and execution limits.

## Execution

Use the existing benchmark command with `--all-incidents`:

```bash
uv run autonomy-lab benchmark \
  --all-incidents \
  --runs 1 \
  --output results/breadth-<provider> \
  --run-interval-seconds <provider-appropriate-interval>
```

The runner preflights every incident output before any pattern execution. Pattern order is deterministically rotated between incidents so the same architecture does not always occupy the first or last attempt position.

Calls inside a pattern are unchanged: parallel fan-out remains concurrent and multi-call workflows keep their original topology. There are no hidden retries.

## Artifacts

Each incident receives the unchanged benchmark artifact set:

```text
INC-xxx/runs.jsonl
INC-xxx/summary.csv
INC-xxx/summary.md
```

The experiment root also receives `breadth-manifest.json`, containing reproducibility metadata and aggregate pattern metrics.

No prompts, model answers, evidence bodies, tool arguments/results, or credentials are persisted.

Historical calibration generations are kept separate and are not recombined with the main breadth generation.

## Experimental boundary

The historical repeated benchmark remains frozen at:

```text
1f8f8b892b033957c73e6260f12edb75e321462c
```

and uses `INC-001`.

The breadth generation is frozen separately at:

```text
bc75739c3eb2949f5f8925cc000ea64af320574d
```

Cross-provider results remain comparisons of provider/model/API/configuration bundles rather than a pure model leaderboard.

## Results

The full breadth analysis, including availability before quality, provider-specific observations, causal-overclaim distribution, routing trajectories, evaluator-optimizer revisions, bounded-agent trajectories, efficiency trade-offs, uncertainty-metric saturation, threats to validity, and explicit non-claims is documented in:

[`MULTI_INCIDENT_BREADTH_RESULTS.md`](MULTI_INCIDENT_BREADTH_RESULTS.md)
