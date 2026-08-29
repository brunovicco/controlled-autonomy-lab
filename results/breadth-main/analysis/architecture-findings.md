# Architecture Findings — Main Breadth Generation

## Experimental scope

- 72 attempted cells: 4 incidents × 6 patterns × 3 provider bundles.
- One run per cell (`n=1`).
- Results are descriptive breadth evidence; no statistical significance claims.
- Quality metrics are calculated only for `status=ok` cells.
- Rate limits and provider errors are availability evidence, not quality zeros.
- Provider comparisons refer to provider/model/API/config bundles, not pure models.
- `uncertainty_preserved` is treated only as lexical uncertainty-language detection.

## Availability

- OpenAI completed 24/24 cells.
- Anthropic completed 23/24 cells; one provider error occurred in INC-003/chaining.
- Groq completed 12/24 cells. All six cells in INC-003 and all six cells in INC-004 were rate-limited.
- Because Groq missingness is incident-blocked rather than pattern-specific, raw 2/4 completion per pattern must not be interpreted as an architecture failure.

## Architecture-level observations

### augmented

- Observed successful cells: 10/12.
- Mean specific grounding across observed cells: 97.8%.
- Total causal overclaims across observed cells: 3.
- Zero-causal-overclaim rate across observed cells: 70.0%.
- Mean model calls: 1.0; mean tool calls: 0.0.
- Mean total tokens: 1264.3; p50 latency: 7690.5585 ms.

### chaining

- Observed successful cells: 9/12.
- Mean specific grounding across observed cells: 74.4%.
- Total causal overclaims across observed cells: 5.
- Zero-causal-overclaim rate across observed cells: 66.7%.
- Mean model calls: 3.0; mean tool calls: 0.0.
- Mean total tokens: 4768.5556; p50 latency: 26339.3 ms.

### routing

- Observed successful cells: 10/12.
- Mean specific grounding across observed cells: 92.8%.
- Total causal overclaims across observed cells: 2.
- Zero-causal-overclaim rate across observed cells: 80.0%.
- Mean model calls: 2.0; mean tool calls: 0.0.
- Mean total tokens: 1560.0; p50 latency: 7151.4255 ms.

### parallel

- Observed successful cells: 10/12.
- Mean specific grounding across observed cells: 94.8%.
- Total causal overclaims across observed cells: 7.
- Zero-causal-overclaim rate across observed cells: 60.0%.
- Mean model calls: 4.0; mean tool calls: 0.0.
- Mean total tokens: 7141.0; p50 latency: 21810.7335 ms.

### evaluator-optimizer

- Observed successful cells: 10/12.
- Mean specific grounding across observed cells: 97.6%.
- Total causal overclaims across observed cells: 4.
- Zero-causal-overclaim rate across observed cells: 70.0%.
- Mean model calls: 2.4; mean tool calls: 0.0.
- Mean total tokens: 3426.8; p50 latency: 9127.149 ms.

### agent

- Observed successful cells: 10/12.
- Mean specific grounding across observed cells: 95.4%.
- Total causal overclaims across observed cells: 0.
- Zero-causal-overclaim rate across observed cells: 100.0%.
- Mean model calls: 2.5; mean tool calls: 4.7.
- Mean total tokens: 3157.6; p50 latency: 7027.9525 ms.

## Interpretation rules for the final report

1. Do not equate grounding with causal correctness.
2. Do not treat non-OK provider cells as zero grounding.
3. Do not infer superiority from latency without accounting for provider bundle differences.
4. Do not infer deterministic architecture behavior from `n=1` cells.
5. Treat trajectory variation as descriptive evidence of control-flow adaptation, not automatically as better reasoning.
