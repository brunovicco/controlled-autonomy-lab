# Breadth Benchmark Visual Evidence

This page provides a compact visual layer over the frozen multi-incident breadth benchmark.

It does not create a new experiment generation or recalculate the benchmark. The figures are direct visualizations of the metadata-only artifacts already published under [`results/breadth-main/`](../results/breadth-main/).

## Experimental boundary

```text
4 incidents × 6 architecture patterns × 1 run × 3 provider bundles
= 72 attempted cells

59 status=ok
12 rate_limited
1 provider_error
```

Quality figures use only `status=ok` cells. Provider/runtime failures remain availability evidence and are not converted into quality zeros.

The experiment uses `n=1` per incident/pattern/provider cell, so the figures are descriptive rather than statistical estimates.

---

## Specific grounding

![Specific grounding by architecture](images/breadth-grounding.svg)

Source: [`results/breadth-main/analysis/architecture-summary.csv`](../results/breadth-main/analysis/architecture-summary.csv)

The chart visualizes mean **specific grounding** over successful cells. Specific grounding checks whether benchmark-defined factual specifics are supported or derivable. It is not a complete semantic-correctness score.

Observed means:

| Pattern | Successful cells | Mean grounding |
| --- | ---: | ---: |
| Augmented | 10 | 97.8% |
| Chaining | 9 | 74.4% |
| Routing | 10 | 92.8% |
| Parallel | 10 | 94.9% |
| Evaluator-optimizer | 10 | 97.6% |
| Agent | 10 | 95.4% |

---

## Detected causal overclaims

![Detected causal overclaims by architecture](images/breadth-causal-overclaims.svg)

Source: [`results/breadth-main/analysis/architecture-summary.csv`](../results/breadth-main/analysis/architecture-summary.csv)

Grounding and causal authority are separate dimensions. A response can mention supported facts while still claiming more causal certainty than the fixture permits.

Detected totals over successful cells:

| Pattern | Causal overclaims | Zero-overclaim cell rate |
| --- | ---: | ---: |
| Augmented | 3 | 70.0% |
| Chaining | 5 | 66.7% |
| Routing | 2 | 80.0% |
| Parallel | 7 | 60.0% |
| Evaluator-optimizer | 4 | 70.0% |
| Agent | 0 | 100.0% |

The agent result is deliberately reported as **zero detected causal overclaims in the observed cells**. It is not proof that agents are universally safer, better, or causally correct.

---

## Provider availability by incident

![Provider availability by incident](images/breadth-availability.svg)

Source: [`results/breadth-main/analysis/availability-by-provider-incident.csv`](../results/breadth-main/analysis/availability-by-provider-incident.csv)

This view makes the missingness structure explicit:

- OpenAI completed all 24 attempted cells;
- Groq completed all cells for `INC-001` and `INC-002`, then all six patterns were rate-limited for both `INC-003` and `INC-004`;
- Anthropic completed 23 of 24 cells, with one provider error in `INC-003 / chaining`.

The Groq pattern therefore reflects provider/time/quota availability in that generation rather than six independent architecture failures.

---

## What the visuals support

The figures make three separate observations easier to inspect:

1. **Grounding is not causal correctness.** High grounding can coexist with causal overclaims.
2. **Architecture changes failure surfaces.** Sequential, parallel, routing, evaluator, and tool-using topologies expose different observable behaviors.
3. **Availability must be separated from quality.** Missing provider cells cannot be treated as zero-quality outputs.

The strongest bounded-agent observation remains narrow:

> Within the observed breadth cells, the bounded tool-using agent was the only architecture pattern with no detected causal overclaims while maintaining high specific grounding.

That result supports further study of bounded autonomy as a mechanism for evidence acquisition and causal restraint. It does not establish a universal architecture winner.

## Canonical sources

- [`MULTI_INCIDENT_BREADTH_BENCHMARK.md`](MULTI_INCIDENT_BREADTH_BENCHMARK.md) — experiment design and frozen boundary
- [`MULTI_INCIDENT_BREADTH_RESULTS.md`](MULTI_INCIDENT_BREADTH_RESULTS.md) — full analysis and threats to validity
- [`results/breadth-main/`](../results/breadth-main/) — metadata-only evidence pack and SHA-256 checksums
- [`architecture-summary.csv`](../results/breadth-main/analysis/architecture-summary.csv) — architecture-level derived metrics
- [`availability-by-provider-incident.csv`](../results/breadth-main/analysis/availability-by-provider-incident.csv) — provider/incident availability matrix
