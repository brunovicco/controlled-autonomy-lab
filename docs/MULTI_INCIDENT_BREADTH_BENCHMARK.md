# Multi-Incident Breadth Benchmark

Phase 3D adds a breadth-first benchmark mode on top of the existing reproducible benchmark runner.

## Experiment shape

The first breadth generation is intentionally one run per incident/pattern/provider bundle:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 executions
```

This experiment asks whether architecture-level behavior observed on `INC-001` persists when the evidence posture changes. It is not a replacement for the frozen 90-run repeated benchmark.

## Canonical incidents

- `INC-001`: correlation without proven current cause
- `INC-002`: deployment cause explicitly confirmed
- `INC-003`: dependency cause explicitly confirmed
- `INC-004`: inconclusive incident requiring abstention

## Execution

Use the existing benchmark command with `--all-incidents`:

```bash
uv run autonomy-lab benchmark   --all-incidents   --runs 1   --output results/breadth-<provider>   --run-interval-seconds <provider-appropriate-interval>
```

The runner preflights every incident output before any pattern execution. Pattern order is deterministically rotated between incidents so the same architecture does not always occupy the first or last attempt position. Calls inside a pattern are unchanged: parallel fan-out remains concurrent and multi-call workflows keep their original topology.

## Artifacts

Each incident receives the unchanged benchmark artifact set:

```text
INC-xxx/runs.jsonl
INC-xxx/summary.csv
INC-xxx/summary.md
```

The experiment root also receives `breadth-manifest.json`, containing only reproducibility metadata and aggregate pattern metrics. No prompts, model answers, evidence bodies, tool arguments/results, or credentials are persisted.

## Experimental boundary

The historical 90-run benchmark remains frozen at `1f8f8b892b033957c73e6260f12edb75e321462c` and `INC-001`. The breadth experiment must be frozen on a new post-Phase-3C commit and reported as a distinct experiment generation. Cross-provider results remain provider/model/API/config bundle comparisons rather than a pure model leaderboard.
