from pathlib import Path


BRANCH = "feat/multi-incident-breadth-benchmark-v3-3"


def patch_cli() -> None:
    path = Path("src/autonomy_lab/cli.py")
    text = path.read_text(encoding="utf-8")

    text = text.replace("import sys\n", "import sys\nimport time\n", 1)
    text = text.replace(
        "from autonomy_lab.domain.benchmark import BenchmarkConfig, BenchmarkStatus\n",
        "from autonomy_lab.domain.benchmark import (\n"
        "    BenchmarkConfig,\n"
        "    BenchmarkRecord,\n"
        "    BenchmarkStatus,\n"
        "    PatternBenchmarkSummary,\n"
        ")\n",
        1,
    )

    marker = "\n\ndef _build_runner(\n"
    replacement = (
        "\n\nBREADTH_INCIDENTS = (\"INC-001\", \"INC-002\", \"INC-003\", \"INC-004\")\n"
        "\n\ndef _build_runner(\n"
    )
    if marker not in text:
        raise SystemExit("runner anchor not found")
    text = text.replace(marker, replacement, 1)

    old_parser = '    benchmark_parser.add_argument("--incident", default="INC-001")\n'
    new_parser = (
        "    benchmark_incidents = benchmark_parser.add_mutually_exclusive_group()\n"
        "    benchmark_incidents.add_argument(\"--incident\", default=\"INC-001\")\n"
        "    benchmark_incidents.add_argument(\n"
        "        \"--all-incidents\",\n"
        "        action=\"store_true\",\n"
        "        help=\"run the benchmark across the canonical four-incident breadth suite\",\n"
        "    )\n"
    )
    if old_parser not in text:
        raise SystemExit("benchmark parser anchor not found")
    text = text.replace(old_parser, new_parser, 1)

    anchor = "\n\ndef _run_reproducible_benchmark(\n"
    breadth = '''


def _rotated_breadth_patterns(incident_index: int) -> tuple[AutonomyPattern, ...]:
    patterns = tuple(AutonomyPattern)
    if not patterns:
        return ()
    offset = incident_index % len(patterns)
    return patterns[offset:] + patterns[:offset]


def _run_breadth_benchmark(
    *,
    args: argparse.Namespace,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> int:
    output_dir = Path(args.output)
    manifest_path = output_dir / "breadth-manifest.json"
    if manifest_path.exists() and not args.overwrite:
        print(
            f"breadth benchmark output already exists: {manifest_path.name}; use --overwrite",
            file=sys.stderr,
        )
        return 2

    environment = benchmark_environment_from_env()
    evaluator = DeterministicGroundingEvaluator()
    canonical_patterns = tuple(AutonomyPattern)
    plans: list[tuple[str, BenchmarkConfig, tuple[AutonomyPattern, ...], Path]] = []

    for incident_index, incident_id in enumerate(BREADTH_INCIDENTS):
        incident_output = output_dir / incident_id
        try:
            assert_benchmark_output_available(incident_output, overwrite=args.overwrite)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        config = BenchmarkConfig(
            incident_id=incident_id,
            runs=args.runs,
            provider=environment.provider,
            model=environment.model,
            max_tokens=environment.max_tokens,
            timeout_seconds=environment.timeout_seconds,
            reasoning_effort=environment.reasoning_effort,
            run_interval_seconds=args.run_interval_seconds,
            git_commit=environment.git_commit,
        )
        plans.append(
            (
                incident_id,
                config,
                _rotated_breadth_patterns(incident_index),
                incident_output,
            )
        )

    completed_plans: list[
        tuple[
            str,
            BenchmarkConfig,
            tuple[BenchmarkRecord, ...],
            tuple[PatternBenchmarkSummary, ...],
            Path,
        ]
    ] = []

    for incident_index, (incident_id, config, execution_patterns, incident_output) in enumerate(
        plans
    ):
        if incident_index > 0 and args.run_interval_seconds > 0:
            time.sleep(args.run_interval_seconds)

        def execute(pattern: AutonomyPattern, active_incident: str = incident_id) -> PatternRun:
            return _build_runner(pattern, store=store, model=model).run(active_incident)

        def evaluate(run: PatternRun) -> GroundingReport:
            return _grounding_for_run(run, store=store, evaluator=evaluator)

        records = run_benchmark(
            config=config,
            patterns=execution_patterns,
            run_pattern=execute,
            evaluate_run=evaluate,
            on_success=lambda run: _record_if_requested(run, args.trace_file),
        )
        summaries = summarize_benchmark(records, patterns=canonical_patterns)
        completed_plans.append((incident_id, config, records, summaries, incident_output))

    for _, config, records, summaries, incident_output in completed_plans:
        write_benchmark_artifacts(
            output_dir=incident_output,
            config=config,
            records=records,
            summaries=summaries,
            overwrite=args.overwrite,
        )

    all_records = tuple(
        record for _, _, records, _, _ in completed_plans for record in records
    )
    aggregate = summarize_benchmark(all_records, patterns=canonical_patterns)
    partial = any(record.status is not BenchmarkStatus.OK for record in all_records)
    rate_limited = sum(record.status is BenchmarkStatus.RATE_LIMITED for record in all_records)
    provider_errors = sum(record.status is BenchmarkStatus.PROVIDER_ERROR for record in all_records)
    completed = sum(record.status is BenchmarkStatus.OK for record in all_records)

    manifest = {
        "schema_version": "breadth-v1",
        "git_commit": environment.git_commit,
        "provider": environment.provider,
        "model": environment.model,
        "max_tokens": environment.max_tokens,
        "timeout_seconds": environment.timeout_seconds,
        "reasoning_effort": environment.reasoning_effort or "default/provider-defined",
        "runs_per_incident_pattern": args.runs,
        "run_interval_seconds": args.run_interval_seconds,
        "incidents": list(BREADTH_INCIDENTS),
        "patterns": [pattern.value for pattern in canonical_patterns],
        "attempted": len(all_records),
        "completed": completed,
        "rate_limited": rate_limited,
        "provider_errors": provider_errors,
        "status": "partial" if partial else "complete",
        "aggregate_by_pattern": [
            {
                "pattern": summary.pattern.value,
                "attempted": summary.attempted,
                "completed": summary.completed,
                "mean_model_calls": summary.mean_model_calls,
                "mean_tool_calls": summary.mean_tool_calls,
                "mean_total_tokens": summary.mean_total_tokens,
                "p50_latency_ms": summary.p50_latency_ms,
                "mean_unsupported": summary.mean_unsupported,
                "mean_proposed": summary.mean_proposed,
                "mean_causality_overclaims": summary.mean_causality_overclaims,
                "mean_grounding_ratio": summary.mean_grounding_ratio,
                "uncertainty_preservation_rate": summary.uncertainty_preservation_rate,
                "unique_trajectories": summary.unique_trajectories,
            }
            for summary in aggregate
        ],
        "artifacts": {
            incident_id: {
                "runs_jsonl": str(incident_output / "runs.jsonl"),
                "summary_csv": str(incident_output / "summary.csv"),
                "summary_markdown": str(incident_output / "summary.md"),
            }
            for incident_id, _, _, _, incident_output in completed_plans
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = manifest_path.with_name(f".{manifest_path.name}.tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)

    print(f"breadth benchmark: {'partial' if partial else 'complete'}")
    print(f"provider:          {environment.provider}")
    print(f"model:             {environment.model}")
    print(f"commit:            {environment.git_commit}")
    print(f"incidents:         {', '.join(BREADTH_INCIDENTS)}")
    print(f"runs:              {args.runs} per incident/pattern")
    print(f"attempts:          {len(all_records)}")
    print(f"completed:         {completed}")
    print(f"manifest:          {manifest_path}")
    print("\npattern | success | p50_ms | grounding | trajectories")
    print("-" * 72)
    for summary in aggregate:
        latency = "-" if summary.p50_latency_ms is None else f"{summary.p50_latency_ms:.1f}"
        grounding = (
            "-" if summary.mean_grounding_ratio is None else f"{summary.mean_grounding_ratio:.1%}"
        )
        print(
            f"{summary.pattern.value} | {summary.completed}/{summary.attempted} | "
            f"{latency} | {grounding} | {summary.unique_trajectories}"
        )
    return 2 if partial else 0
'''
    if anchor not in text:
        raise SystemExit("benchmark function anchor not found")
    text = text.replace(anchor, breadth + anchor, 1)

    old_start = '''def _run_reproducible_benchmark(
    *,
    args: argparse.Namespace,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> int:
    output_dir = Path(args.output)
'''
    new_start = '''def _run_reproducible_benchmark(
    *,
    args: argparse.Namespace,
    store: InMemoryIncidentStore,
    model: ModelClient,
) -> int:
    if args.all_incidents:
        return _run_breadth_benchmark(args=args, store=store, model=model)

    output_dir = Path(args.output)
'''
    if old_start not in text:
        raise SystemExit("reproducible benchmark anchor not found")
    text = text.replace(old_start, new_start, 1)
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    path = Path("tests/unit/test_benchmark_cli.py")
    text = path.read_text(encoding="utf-8")
    marker = "def test_benchmark_all_incidents_writes_breadth_manifest_and_four_artifact_sets("
    if marker in text:
        return
    text += '''


def test_benchmark_all_incidents_writes_breadth_manifest_and_four_artifact_sets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_benchmark_dependencies(monkeypatch)
    output = tmp_path / "breadth"

    exit_code = cli.main(
        [
            "benchmark",
            "--all-incidents",
            "--runs",
            "1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "breadth benchmark: complete" in capsys.readouterr().out
    manifest = json.loads((output / "breadth-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "breadth-v1"
    assert manifest["incidents"] == ["INC-001", "INC-002", "INC-003", "INC-004"]
    assert manifest["attempted"] == 24
    assert manifest["completed"] == 24
    assert manifest["status"] == "complete"
    assert len(manifest["aggregate_by_pattern"]) == len(AutonomyPattern)

    expected_first_pattern = {
        "INC-001": "augmented",
        "INC-002": "chaining",
        "INC-003": "routing",
        "INC-004": "parallel",
    }
    for incident_id in manifest["incidents"]:
        records = [
            json.loads(line)
            for line in (output / incident_id / "runs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert len(records) == len(AutonomyPattern)
        assert records[0]["pattern"] == expected_first_pattern[incident_id]
        assert all(record["incident_id"] == incident_id for record in records)
        assert all(record["status"] == "ok" for record in records)
        assert all("answer" not in record for record in records)


def test_benchmark_all_incidents_preflights_every_output_before_pattern_calls(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_benchmark_dependencies(monkeypatch)
    output = tmp_path / "breadth"
    blocked = output / "INC-003"
    blocked.mkdir(parents=True)
    (blocked / "summary.md").write_text("existing", encoding="utf-8")
    pattern_calls = 0

    def build_runner(
        pattern: AutonomyPattern,
        *,
        store: object,
        model: object,
    ) -> StaticRunner:
        nonlocal pattern_calls
        del store, model
        pattern_calls += 1
        return StaticRunner(pattern)

    monkeypatch.setattr(cli, "_build_runner", build_runner)

    exit_code = cli.main(
        ["benchmark", "--all-incidents", "--runs", "1", "--output", str(output)]
    )

    assert exit_code == 2
    assert pattern_calls == 0
    assert "benchmark output already exists" in capsys.readouterr().err
'''
    path.write_text(text, encoding="utf-8")


def write_docs() -> None:
    Path("docs/MULTI_INCIDENT_BREADTH_BENCHMARK.md").write_text(
        """# Multi-Incident Breadth Benchmark

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
uv run autonomy-lab benchmark \
  --all-incidents \
  --runs 1 \
  --output results/breadth-<provider> \
  --run-interval-seconds <provider-appropriate-interval>
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
""",
        encoding="utf-8",
    )


def main() -> None:
    patch_cli()
    patch_tests()
    write_docs()


if __name__ == "__main__":
    main()
