# Epistemic Evaluation v4.1 — Calibration Cases

These static cases calibrate causal posture without provider calls.

They are deliberately separate from the frozen breadth generation and do not reclassify historical benchmark outputs.

| Incident | Evidence posture | Example answer posture | Expected verdict |
| --- | --- | --- | --- |
| `INC-001` | correlational | qualified causal hypothesis + explicit non-causality | `aligned` |
| `INC-001` | correlational | unqualified deployment causality | `overclaimed` |
| `INC-001` | correlational | facts only, no causal posture | `no-position` |
| `INC-002` | confirmed cause | direct supported deployment causality | `aligned` |
| `INC-002` | confirmed cause | supported cause kept hypothetical | `over-hedged` |
| `INC-003` | confirmed cause | direct supported dependency causality | `aligned` |
| `INC-004` | inconclusive | explicit non-attribution / abstention | `aligned` |
| `INC-004` | inconclusive | `likely caused` without abstention | `insufficient-abstention` |
| `INC-004` | inconclusive | strong causal attribution | `overclaimed` |

The calibration also includes a historical-context case to ensure a causal statement about another incident does not define the current incident posture.

## Key discriminator

The most important regression is:

```text
The identity-provider latency likely caused the incident.
```

For `INC-004`, this sentence contains lexical uncertainty (`likely`) but does not abstain from causal attribution.

Therefore:

```text
uncertainty_language_detected = true
verdict = insufficient-abstention
```

This is the behavior that the historical lexical uncertainty flag could not express.
