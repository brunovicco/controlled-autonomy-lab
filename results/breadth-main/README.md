# Multi-Incident Breadth Evidence Pack

This directory contains the curated, metadata-only evidence pack for the
Controlled Autonomy Lab multi-incident breadth benchmark.

## Frozen generation

```text
git commit:
bc75739c3eb2949f5f8925cc000ea64af320574d

4 incidents
× 6 architecture patterns
× 1 run
× 3 provider/model/configuration bundles
= 72 attempted cells
```

Observed execution:

| Status | Cells |
| --- | ---: |
| `ok` | 59 |
| `rate_limited` | 12 |
| `provider_error` | 1 |
| **Total** | **72** |

Non-OK cells are availability/runtime evidence. They are not assigned
zero grounding or other imputed quality values.

## Directory structure

```text
breadth-main/
├── README.md
├── generation-manifest.json
├── SHA256SUMS
├── raw/
│   ├── openai/
│   ├── groq/
│   └── anthropic/
└── analysis/
```

### `raw/`

Contains the canonical provider generation manifests and `runs.jsonl`
records for each of the four incidents.

The raw records are deliberately metadata-only.

They may contain:

- provider/model identity;
- incident and architecture pattern;
- execution status;
- latency and usage metadata;
- model/tool call counts;
- grounding and causal-evaluation metadata;
- successful execution trajectories.

They deliberately exclude:

- prompts;
- complete model answers;
- evidence bodies;
- tool arguments;
- tool results;
- credentials or API keys.

### `analysis/`

Contains deterministic derived tables used by the published breadth
analysis.

The canonical 72-cell table is:

```text
analysis/cells-72.csv
```

Other files provide availability, architecture, causal, incident,
provider, and trajectory views derived from that generation.

## Interpretation boundary

This evidence pack supports descriptive inspection of one run per
incident/pattern/provider cell.

It does not establish:

- statistical significance;
- universal model rankings;
- universal architecture rankings;
- that zero detected causal overclaims proves universal correctness;
- that provider token counts are directly comparable accounting units;
- that live-service latency is a service-level guarantee.

Provider comparisons refer to provider/model/API/configuration bundles.

Quality metrics are calculated only on successful (`status=ok`) cells.

## Published analysis

See:

- `../../docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md`
- `../../docs/MULTI_INCIDENT_BREADTH_RESULTS.md`

Historical calibration generations are intentionally excluded from this
pack and must not be recombined with the main generation.
