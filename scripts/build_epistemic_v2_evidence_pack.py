from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from statistics import mean, median
from typing import Any

FREEZE = "06e108f5ed7bc3a74e01682538a4bcd23f7d3023"
INCIDENTS = ("INC-001", "INC-002", "INC-003", "INC-004")
PATTERNS = (
    "augmented",
    "chaining",
    "routing",
    "parallel",
    "evaluator-optimizer",
    "agent",
)
PROVIDER_ORDER = ("openai", "anthropic", "groq")

PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "source": "epistemic-v4-1-openai",
        "model": "gpt-5.6-luna",
        "max_tokens": 4000,
        "timeout_seconds": 60.0,
        "run_interval_seconds": 2.0,
        "expected_statuses": Counter({"ok": 24}),
    },
    "anthropic": {
        "source": "epistemic-v4-1-anthropic",
        "model": "claude-sonnet-5",
        "max_tokens": 4000,
        "timeout_seconds": 60.0,
        "run_interval_seconds": 10.0,
        "expected_statuses": Counter({"ok": 24}),
    },
    "groq": {
        "source": "epistemic-v4-1-groq",
        "model": "openai/gpt-oss-20b",
        "max_tokens": 900,
        "timeout_seconds": 30.0,
        "run_interval_seconds": 30.0,
        "expected_statuses": Counter({"ok": 22, "rate_limited": 1, "provider_error": 1}),
    },
}

FORBIDDEN_KEYS = {
    "prompt",
    "prompts",
    "answer",
    "answers",
    "response",
    "responses",
    "evidence",
    "evidence_body",
    "tool_args",
    "tool_arguments",
    "tool_result",
    "tool_results",
    "credential",
    "credentials",
    "api_key",
    "api_keys",
    "secret",
    "secrets",
}

CELL_FIELDS = (
    "schema_version",
    "grounding_evaluation_version",
    "epistemic_evaluation_version",
    "git_commit",
    "provider",
    "model",
    "max_tokens",
    "timeout_seconds",
    "reasoning_effort",
    "run_interval_seconds",
    "incident_id",
    "pattern",
    "run_number",
    "status",
    "model_calls",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "unsupported_count",
    "proposed_count",
    "causality_overclaims",
    "grounding_ratio",
    "uncertainty_preserved",
    "epistemic_expected_posture",
    "epistemic_verdict",
    "epistemic_aligned",
    "causal_assertion_detected",
    "hedged_causal_language_detected",
    "abstention_detected",
    "uncertainty_language_detected",
    "trajectory",
    "retry_after",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the frozen Epistemic v4.1 metadata-only evidence pack."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("results"),
        help="directory containing the three frozen provider result directories",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/epistemic-v4-1-main"),
        help="curated evidence-pack output directory",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object: {path}:{line_number}")
        rows.append(payload)
    return rows


def _scan_forbidden(value: Any, *, location: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden persistence field {key!r} at {location}")
            _scan_forbidden(nested, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _scan_forbidden(nested, location=f"{location}[{index}]")


def _expect_equal(actual: Any, expected: Any, *, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def _validate_manifest(provider: str, manifest: Mapping[str, Any]) -> None:
    expected = PROVIDERS[provider]
    _expect_equal(manifest.get("schema_version"), "breadth-v2", label=f"{provider} schema")
    _expect_equal(
        manifest.get("record_schema_version"),
        "benchmark-record-v2",
        label=f"{provider} record schema",
    )
    _expect_equal(
        manifest.get("summary_schema_version"),
        "benchmark-summary-v2",
        label=f"{provider} summary schema",
    )
    _expect_equal(
        manifest.get("grounding_evaluation_version"),
        "grounding-v1",
        label=f"{provider} grounding evaluator",
    )
    _expect_equal(
        manifest.get("epistemic_evaluation_version"),
        "epistemic-v4.1",
        label=f"{provider} epistemic evaluator",
    )
    _expect_equal(manifest.get("git_commit"), FREEZE, label=f"{provider} freeze")
    _expect_equal(manifest.get("provider"), provider, label=f"{provider} provider")
    _expect_equal(manifest.get("model"), expected["model"], label=f"{provider} model")
    _expect_equal(
        manifest.get("max_tokens"), expected["max_tokens"], label=f"{provider} max_tokens"
    )
    _expect_equal(
        float(manifest.get("timeout_seconds")),
        expected["timeout_seconds"],
        label=f"{provider} timeout",
    )
    _expect_equal(
        float(manifest.get("run_interval_seconds")),
        expected["run_interval_seconds"],
        label=f"{provider} interval",
    )
    _expect_equal(manifest.get("attempted"), 24, label=f"{provider} attempted")


def _validate_record(provider: str, row: Mapping[str, Any]) -> None:
    expected = PROVIDERS[provider]
    _expect_equal(row.get("schema_version"), "benchmark-record-v2", label="record schema")
    _expect_equal(row.get("grounding_evaluation_version"), "grounding-v1", label="grounding")
    _expect_equal(row.get("epistemic_evaluation_version"), "epistemic-v4.1", label="epistemic")
    _expect_equal(row.get("git_commit"), FREEZE, label="record freeze")
    _expect_equal(row.get("provider"), provider, label="record provider")
    _expect_equal(row.get("model"), expected["model"], label="record model")
    if row.get("incident_id") not in INCIDENTS:
        raise ValueError(f"unknown incident: {row.get('incident_id')!r}")
    if row.get("pattern") not in PATTERNS:
        raise ValueError(f"unknown pattern: {row.get('pattern')!r}")
    if row.get("status") != "ok" and (
        row.get("epistemic_verdict") is not None or row.get("epistemic_aligned") is not None
    ):
        raise ValueError("non-OK record contains epistemic quality verdict")


def _copy_provider(
    *,
    provider: str,
    source_root: Path,
    raw_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = PROVIDERS[provider]
    source = source_root / str(config["source"])
    manifest_path = source / "breadth-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    manifest = _load_json(manifest_path)
    _scan_forbidden(manifest, location=str(manifest_path))
    _validate_manifest(provider, manifest)

    destination = raw_root / provider
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, destination / "breadth-manifest.json")

    rows: list[dict[str, Any]] = []
    for incident in INCIDENTS:
        source_runs = source / incident / "runs.jsonl"
        incident_rows = _load_jsonl(source_runs)
        if len(incident_rows) != len(PATTERNS):
            raise ValueError(
                f"{provider}/{incident}: expected 6 records, found {len(incident_rows)}"
            )
        for row in incident_rows:
            _scan_forbidden(row, location=f"{source_runs}:{row.get('pattern')}")
            _validate_record(provider, row)
        rows.extend(incident_rows)

        destination_incident = destination / incident
        destination_incident.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_runs, destination_incident / "runs.jsonl")

    if len(rows) != 24:
        raise ValueError(f"{provider}: expected 24 records, found {len(rows)}")

    statuses = Counter(str(row["status"]) for row in rows)
    expected_statuses: Counter[str] = config["expected_statuses"]
    if statuses != expected_statuses:
        raise ValueError(
            f"{provider}: expected statuses {dict(expected_statuses)}, found {dict(statuses)}"
        )

    cells = {(str(row["incident_id"]), str(row["pattern"])) for row in rows}
    if len(cells) != 24:
        raise ValueError(f"{provider}: duplicate or missing incident/pattern cells")

    print(f"{provider:<10}: 24 metadata-only records validated; statuses={dict(statuses)}")
    return manifest, rows


def _trajectory_text(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return " -> ".join(str(item) for item in value)


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _cell_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    order_provider = {value: index for index, value in enumerate(PROVIDER_ORDER)}
    order_incident = {value: index for index, value in enumerate(INCIDENTS)}
    order_pattern = {value: index for index, value in enumerate(PATTERNS)}
    ordered = sorted(
        rows,
        key=lambda row: (
            order_provider[str(row["provider"])],
            order_incident[str(row["incident_id"])],
            order_pattern[str(row["pattern"])],
        ),
    )
    result: list[dict[str, Any]] = []
    for row in ordered:
        payload = {field: row.get(field) for field in CELL_FIELDS}
        payload["trajectory"] = _trajectory_text(row.get("trajectory"))
        result.append(payload)
    return result


def _float_values(rows: Iterable[Mapping[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is not None:
            values.append(float(value))
    return values


def _mean(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = _float_values(rows, key)
    return mean(values) if values else None


def _median(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = _float_values(rows, key)
    return median(values) if values else None


def _summary_row(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if row.get("status") == "ok"]
    statuses = Counter(str(row["status"]) for row in rows)
    verdicts = Counter(str(row["epistemic_verdict"]) for row in successful)
    aligned = verdicts.get("aligned", 0)
    overclaimed = verdicts.get("overclaimed", 0)
    return {
        "attempted": len(rows),
        "ok": statuses.get("ok", 0),
        "rate_limited": statuses.get("rate_limited", 0),
        "provider_error": statuses.get("provider_error", 0),
        "bound_exceeded": statuses.get("bound_exceeded", 0),
        "completion_rate": round(len(successful) / len(rows), 6) if rows else None,
        "aligned": aligned,
        "alignment_rate": round(aligned / len(successful), 6) if successful else None,
        "overclaimed": overclaimed,
        "overclaim_rate": round(overclaimed / len(successful), 6) if successful else None,
        "no_position": verdicts.get("no-position", 0),
        "over_hedged": verdicts.get("over-hedged", 0),
        "insufficient_abstention": verdicts.get("insufficient-abstention", 0),
        "mean_grounding_ratio": _mean(successful, "grounding_ratio"),
        "mean_causality_overclaims": _mean(successful, "causality_overclaims"),
        "mean_model_calls": _mean(successful, "model_calls"),
        "mean_tool_calls": _mean(successful, "tool_calls"),
        "mean_total_tokens": (
            mean(
                float(row.get("input_tokens") or 0) + float(row.get("output_tokens") or 0)
                for row in successful
            )
            if successful
            else None
        ),
        "p50_latency_ms": _median(successful, "latency_ms"),
    }


def _group_rows(
    rows: Sequence[Mapping[str, Any]],
    key_names: Sequence[str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row[name]) for name in key_names)
        grouped[key].append(row)

    result: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        summary = _summary_row(group)
        for name, value in zip(key_names, key, strict=True):
            summary[name] = value
        result.append(summary)
    return result


def _write_summary_csv(path: Path, rows: Sequence[dict[str, Any]], keys: Sequence[str]) -> None:
    metrics = (
        "attempted",
        "ok",
        "rate_limited",
        "provider_error",
        "bound_exceeded",
        "completion_rate",
        "aligned",
        "alignment_rate",
        "overclaimed",
        "overclaim_rate",
        "no_position",
        "over_hedged",
        "insufficient_abstention",
        "mean_grounding_ratio",
        "mean_causality_overclaims",
        "mean_model_calls",
        "mean_tool_calls",
        "mean_total_tokens",
        "p50_latency_ms",
    )
    _write_csv(path, (*keys, *metrics), rows)


def _successful_trajectories(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "ok":
            continue
        result.append(
            {
                "provider": row["provider"],
                "incident_id": row["incident_id"],
                "pattern": row["pattern"],
                "model_calls": row.get("model_calls"),
                "tool_calls": row.get("tool_calls"),
                "epistemic_verdict": row.get("epistemic_verdict"),
                "trajectory": _trajectory_text(row.get("trajectory")),
            }
        )
    return result


def _write_readme(output: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    successful = [row for row in rows if row.get("status") == "ok"]
    statuses = Counter(str(row["status"]) for row in rows)
    verdicts = Counter(str(row["epistemic_verdict"]) for row in successful)
    content = f"""# Epistemic v4.1 Evidence Pack

Frozen implementation:

`{FREEZE}`

Experiment shape:

`4 incidents x 6 architecture patterns x 1 run x 3 provider bundles = 72 attempts`

Observed execution:

- {statuses.get("ok", 0)} successful cells;
- {statuses.get("rate_limited", 0)} rate-limited cell;
- {statuses.get("provider_error", 0)} provider-error cell;
- {statuses.get("bound_exceeded", 0)} bound-exceeded cells.

Successful-cell Epistemic v4.1 verdicts:

- {verdicts.get("aligned", 0)} aligned;
- {verdicts.get("overclaimed", 0)} overclaimed;
- {verdicts.get("no-position", 0)} no-position;
- {verdicts.get("over-hedged", 0)} over-hedged;
- {verdicts.get("insufficient-abstention", 0)} insufficient-abstention.

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
"""
    (output / "README.md").write_text(content, encoding="utf-8")


def _write_generation_manifest(
    output: Path,
    manifests: Mapping[str, Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    statuses = Counter(str(row["status"]) for row in rows)
    payload = {
        "schema_version": "epistemic-evidence-pack-v1",
        "git_commit": FREEZE,
        "record_schema_version": "benchmark-record-v2",
        "grounding_evaluation_version": "grounding-v1",
        "epistemic_evaluation_version": "epistemic-v4.1",
        "attempted": len(rows),
        "statuses": dict(sorted(statuses.items())),
        "providers": {
            provider: {
                "model": manifest["model"],
                "max_tokens": manifest["max_tokens"],
                "timeout_seconds": manifest["timeout_seconds"],
                "run_interval_seconds": manifest["run_interval_seconds"],
                "reasoning_effort": manifest["reasoning_effort"],
            }
            for provider, manifest in manifests.items()
        },
        "generation_boundary": (
            "new frozen generation; do not mix with historical breadth-v1 quality aggregates"
        ),
    }
    (output / "generation-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _checksums(output: Path) -> None:
    lines: list[str] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(output).as_posix()
        lines.append(f"{digest}  {relative}")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate_output(output: Path) -> None:
    for path in sorted(output.rglob("*.json")):
        _scan_forbidden(_load_json(path), location=str(path))
    for path in sorted(output.rglob("*.jsonl")):
        for index, payload in enumerate(_load_jsonl(path), start=1):
            _scan_forbidden(payload, location=f"{path}:{index}")


def main() -> int:
    args = _parser().parse_args()
    source_root: Path = args.source_root.resolve()
    output: Path = args.output.resolve()
    if output.exists():
        raise SystemExit(f"output already exists: {output}")

    raw_root = output / "raw"
    analysis_root = output / "analysis"
    output.mkdir(parents=True)

    manifests: dict[str, dict[str, Any]] = {}
    all_rows: list[dict[str, Any]] = []
    try:
        for provider in PROVIDER_ORDER:
            manifest, rows = _copy_provider(
                provider=provider,
                source_root=source_root,
                raw_root=raw_root,
            )
            manifests[provider] = manifest
            all_rows.extend(rows)

        if len(all_rows) != 72:
            raise ValueError(f"expected 72 canonical records, found {len(all_rows)}")

        canonical = {
            (str(row["provider"]), str(row["incident_id"]), str(row["pattern"])) for row in all_rows
        }
        if len(canonical) != 72:
            raise ValueError("duplicate or missing provider/incident/pattern cells")

        cells = _cell_rows(all_rows)
        _write_csv(analysis_root / "cells-72.csv", CELL_FIELDS, cells)

        provider_rows = _group_rows(all_rows, ("provider",))
        incident_rows = _group_rows(all_rows, ("incident_id",))
        pattern_rows = _group_rows(all_rows, ("pattern",))
        provider_incident_rows = _group_rows(all_rows, ("provider", "incident_id"))
        incident_pattern_rows = _group_rows(all_rows, ("incident_id", "pattern"))

        _write_summary_csv(analysis_root / "provider-summary.csv", provider_rows, ("provider",))
        _write_summary_csv(analysis_root / "incident-summary.csv", incident_rows, ("incident_id",))
        _write_summary_csv(analysis_root / "pattern-summary.csv", pattern_rows, ("pattern",))
        _write_summary_csv(
            analysis_root / "provider-incident-summary.csv",
            provider_incident_rows,
            ("provider", "incident_id"),
        )
        _write_summary_csv(
            analysis_root / "incident-pattern-summary.csv",
            incident_pattern_rows,
            ("incident_id", "pattern"),
        )
        trajectories = _successful_trajectories(all_rows)
        _write_csv(
            analysis_root / "successful-trajectories.csv",
            (
                "provider",
                "incident_id",
                "pattern",
                "model_calls",
                "tool_calls",
                "epistemic_verdict",
                "trajectory",
            ),
            trajectories,
        )

        _write_generation_manifest(output, manifests, all_rows)
        _write_readme(output, all_rows)
        _validate_output(output)
        _checksums(output)
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise

    statuses = Counter(str(row["status"]) for row in all_rows)
    verdicts = Counter(
        str(row["epistemic_verdict"]) for row in all_rows if row.get("status") == "ok"
    )
    print()
    print("=== Epistemic v4.1 evidence pack ===")
    print(f"freeze:       {FREEZE}")
    print(f"attempted:    {len(all_rows)}")
    print(f"statuses:     {dict(statuses)}")
    print(f"verdicts:     {dict(verdicts)}")
    print(f"output:       {output}")
    print("forbidden persistence fields: NONE")
    print("evidence-pack generation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
