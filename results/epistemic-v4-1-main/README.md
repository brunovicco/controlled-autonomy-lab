# Epistemic v4.1 Evidence Pack

Frozen implementation:

`06e108f5ed7bc3a74e01682538a4bcd23f7d3023`

Experiment shape:

`4 incidents x 6 architecture patterns x 1 run x 3 provider bundles = 72 attempts`

Observed execution:

- 70 successful cells;
- 1 rate-limited cell;
- 1 provider-error cell;
- 0 bound-exceeded cells.

Successful-cell Epistemic v4.1 verdicts:

- 20 aligned;
- 41 overclaimed;
- 6 no-position;
- 3 over-hedged;
- 0 insufficient-abstention.

## Evidence chain

```text
frozen provider metadata
        ↓
72 canonical cells
        ↓
derived availability / grounding / epistemic summaries
        ↓
public results report
```

## Raw metadata

`raw/` contains only the provider breadth manifests and metadata-only `runs.jsonl` files used
for this generation. Full prompts, complete answers, evidence bodies, tool arguments/results,
credentials, and API keys are intentionally excluded.

## Derived analysis

`analysis/` contains deterministic tables generated from the 72 canonical records. Quality and
Epistemic v4.1 aggregates use only `status=ok` cells. Provider/runtime failures remain availability
evidence and are not converted into quality zeros.

## Interpretation boundary

This generation has `n=1` per provider/incident/pattern cell. Findings are descriptive rather than
statistically significant. `overclaimed` means detected under deterministic Epistemic v4.1; it is
not universal proof of semantic causal error. Provider comparisons refer to provider/model/API/
configuration bundles.

See `docs/EPISTEMIC_GENERATION_V2_RESULTS.md` for the complete interpretation and explicit
non-claims.
