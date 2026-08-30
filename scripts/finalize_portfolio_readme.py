from pathlib import Path


README = Path("README.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label}, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    text = README.read_text()

    title = "# Controlled Autonomy Lab\n\n"
    title_with_badges = """# Controlled Autonomy Lab

[![quality](https://github.com/brunovicco/controlled-autonomy-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/controlled-autonomy-lab/actions/workflows/quality.yml)
![Python](https://img.shields.io/badge/python-3.13%20%7C%203.14-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

"""
    text = replace_once(text, title, title_with_badges, "README title")

    intro_end = (
        "The lab makes that delegation boundary observable through execution topology, tool use, "
        "latency, token usage, deterministic grounding, claim-level evaluation, causal-authority "
        "checks, and selective semantic judgement.\n\n"
    )
    at_a_glance = """The lab makes that delegation boundary observable through execution topology, tool use, latency, token usage, deterministic grounding, claim-level evaluation, causal-authority checks, and selective semantic judgement.

## Case at a glance

| Dimension | Scope |
| --- | --- |
| Control patterns | 6 — augmented, chaining, routing, parallel, evaluator-optimizer, bounded agent |
| Provider bundles | OpenAI, Anthropic, Groq |
| Frozen experimental record | 90 repeated executions + 72 breadth attempts + 72 epistemic attempts |
| Evaluation layers | Grounding v1, Epistemic v4.1, Claim Evaluation v2, selective semantic escalation |
| Agent authority | 5 read-only tools, max 6 steps, max 8 tool calls, no production writes |
| Reproducibility | frozen commits, metadata-only evidence packs, SHA-256 checksums, no hidden retries |

Across the three separate frozen generations, the repository records **234 executions/attempted cells**. They are intentionally kept as separate generations and are **not** pooled as one statistical sample.

```mermaid
flowchart LR
    A[Augmented] --> B[Chaining]
    B --> C[Routing]
    C --> D[Parallel]
    D --> E[Evaluator-optimizer]
    E --> F[Bounded agent]
    A -. application owns path .-> E
    F -. model owns next step within bounds .-> F
```

Three findings motivate the case:

- **grounding is not the same as causal discipline**;
- **provider/model behavior can become control-plane behavior** when a model selects the next step;
- **bounded autonomy is not unrestricted authority** — the agent can gather evidence dynamically while deterministic code retains hard execution limits.

"""
    text = replace_once(text, intro_end, at_a_glance, "README introduction")

    docs_marker = (
        "- [`docs/GROUNDING.md`](docs/GROUNDING.md) — deterministic Grounding v1\n"
    )
    docs_replacement = """- [`docs/EPISTEMIC_EVALUATION.md`](docs/EPISTEMIC_EVALUATION.md) — deterministic evidence-posture and causal-authority evaluation
- [`docs/EPISTEMIC_BENCHMARK_GENERATION_V2.md`](docs/EPISTEMIC_BENCHMARK_GENERATION_V2.md) — Epistemic v4.1 generation protocol and freeze boundary
- [`docs/EPISTEMIC_GENERATION_V2_RESULTS.md`](docs/EPISTEMIC_GENERATION_V2_RESULTS.md) — frozen 72-cell epistemic generation analysis
- [`docs/GROUNDING.md`](docs/GROUNDING.md) — deterministic Grounding v1
"""
    text = replace_once(text, docs_marker, docs_replacement, "documentation index marker")

    references_marker = "## References\n"
    license_section = """## License

Licensed under the [Apache License 2.0](LICENSE).

## References
"""
    text = replace_once(text, references_marker, license_section, "References heading")

    README.write_text(text)


if __name__ == "__main__":
    main()
