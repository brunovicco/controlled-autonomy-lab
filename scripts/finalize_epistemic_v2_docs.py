from pathlib import Path


RESULTS_PATH = Path("docs/EPISTEMIC_GENERATION_V2_RESULTS.md")
README_PATH = Path("README.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one {label} block, found {text.count(old)}")
    return text.replace(old, new, 1)


def update_results() -> None:
    text = RESULTS_PATH.read_text()
    old = """# Next step

The next publication step is a curated metadata-only evidence pack containing:

1. the three provider generation manifests;
2. all 72 metadata-only benchmark records;
3. canonical consolidated cells;
4. availability summaries;
5. incident/pattern/provider epistemic summaries;
6. Grounding v1 × Epistemic v4.1 comparison tables;
7. trajectory metadata;
8. recursive persistence-safety validation;
9. SHA-256 checksums.

The evidence pack must be derived from the frozen local generation outputs without rerunning any model calls.
"""
    new = """# Published evidence pack

The curated metadata-only evidence pack is published at:

[`results/epistemic-v4-1-main/`](../results/epistemic-v4-1-main/)

It contains the three provider generation manifests, all 72 metadata-only benchmark records, canonical consolidated cells, provider/incident/pattern summaries, successful trajectory metadata, a generation manifest, and SHA-256 checksums.

The pack was built offline from the frozen provider outputs. No model calls were rerun to create the publication artifacts.
"""
    RESULTS_PATH.write_text(replace_once(text, old, new, "results publication"))


def update_readme() -> None:
    text = README_PATH.read_text()

    old_pipeline = """Grounding Evaluation v1
exact specifics, associations, causal discipline
      ↓
Claim Evaluation v2
fact vs inference vs action vs unsupported claim
"""
    new_pipeline = """Grounding Evaluation v1
exact specifics, associations, causal discipline
      ↓
Epistemic Evaluation v4.1
evidence posture and causal-authority alignment
      ↓
Claim Evaluation v2
fact vs inference vs action vs unsupported claim
"""
    text = replace_once(text, old_pipeline, new_pipeline, "README evaluation pipeline")

    marker = "### Claim-level calibration\n"
    section = """### Epistemic posture benchmark

A new frozen generation evaluates whether final-answer causal authority matches the evidence posture:

```text
4 incidents × 6 patterns × 1 run × 3 provider bundles = 72 attempted cells
```

The generation produced **70 successful cells**, with one Groq rate-limited cell and one Groq provider-error cell preserved as availability evidence.

Epistemic v4.1 verdicts across successful cells were:

| Verdict | Count | Share |
| --- | ---: | ---: |
| Aligned | 20 | 28.6% |
| Overclaimed | 41 | 58.6% |
| No-position | 6 | 8.6% |
| Over-hedged | 3 | 4.3% |

`INC-001` and `INC-004`, the two fixtures requiring the greatest causal restraint, accounted for **29/41 detected overclaims (~70.7%)**. Among the fully observed patterns, the bounded tool-using agent had the lowest detected-overclaim rate in this generation at **4/12 (33.3%)**.

These are deterministic **detected verdicts under Epistemic v4.1**, not proof of semantic causal error. The result does not establish that agents are universally safer or better.

See:

- [`docs/EPISTEMIC_EVALUATION.md`](docs/EPISTEMIC_EVALUATION.md) for evaluator semantics and limitations;
- [`docs/EPISTEMIC_GENERATION_V2_RESULTS.md`](docs/EPISTEMIC_GENERATION_V2_RESULTS.md) for the frozen analysis and non-claims;
- [`results/epistemic-v4-1-main/`](results/epistemic-v4-1-main/) for the metadata-only evidence pack and SHA-256 checksums.

"""
    if text.count(marker) != 1:
        raise RuntimeError(f"expected exactly one README claim calibration marker, found {text.count(marker)}")
    text = text.replace(marker, section + marker, 1)

    old_next = """1. design a posture-aware epistemic metric that distinguishes appropriate uncertainty from lexical hedging;
2. add repeated runs to selected breadth cells to measure variance without mixing generations;
3. add provider-aware cost normalization while preserving raw provider token metadata;
4. expand incident fixtures only as new frozen experiment generations;
5. consider a real remote evaluator/evidence boundary before introducing A2A/MCP infrastructure.
"""
    new_next = """1. calibrate Epistemic v4.1 against a larger static labelled posture corpus before adding semantic escalation;
2. add repeated runs to selected breadth cells to measure variance without mixing generations;
3. add provider-aware cost normalization while preserving raw provider token metadata;
4. expand incident fixtures only as new frozen experiment generations;
5. consider a real remote evaluator/evidence boundary before introducing A2A/MCP infrastructure.
"""
    README_PATH.write_text(replace_once(text, old_next, new_next, "README next experiments"))


def main() -> None:
    update_results()
    update_readme()


if __name__ == "__main__":
    main()
