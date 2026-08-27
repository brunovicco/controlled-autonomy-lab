"""Evaluate the packaged human-labelled claim set and optional semantic judge."""

import argparse
import json
import sys

from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.labelled_claims import LabelledClaimSetError, load_labelled_claims_v1
from autonomy_lab.adapters.providers import ProviderSelection, semantic_client_from_env
from autonomy_lab.application.claim_matrix import ClaimJudgeMatrixRunner, ClaimMatrixError
from autonomy_lab.application.model_errors import ModelProviderError
from autonomy_lab.application.semantic_claim_evaluation import (
    SemanticClaimEvaluationError,
    SemanticClaimEvaluatorV21,
)
from autonomy_lab.domain.claim_matrix import ClaimMatrixReport


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse claim-matrix calibration options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Evaluate eligible deterministic misses with the configured SEMANTIC_* judge",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    return parser.parse_args(argv)


def _selection_payload(selection: ProviderSelection | None) -> dict[str, object] | None:
    if selection is None:
        return None
    return {
        "provider": selection.provider,
        "model": selection.model,
        "max_tokens": selection.max_tokens,
        "timeout_seconds": selection.timeout_seconds,
    }


def _report_payload(
    report: ClaimMatrixReport,
    *,
    judge: ProviderSelection | None,
    semantic_error: str | None = None,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for row in report.rows:
        rows.append(
            {
                "case_id": row.case_id,
                "category": row.category,
                "claim": row.claim,
                "expected_kind": row.expected_kind.value,
                "deterministic": {
                    "kind": row.deterministic_kind.value,
                    "correct": row.deterministic_correct,
                    "rationale": row.deterministic_rationale,
                    "evidence_sources": list(row.deterministic_evidence_sources),
                },
                "semantic": (
                    {
                        "kind": row.semantic_kind.value if row.semantic_kind is not None else None,
                        "rationale": row.semantic_rationale,
                        "evidence_sources": list(row.semantic_evidence_sources),
                    }
                    if row.semantic_evaluated
                    else None
                ),
                "final": {
                    "kind": row.final_kind.value,
                    "correct": row.final_correct,
                },
                "disagreement": row.disagreement,
                "resolution": row.resolution,
            }
        )

    return {
        "claim_set": {
            "name": report.claim_set.name,
            "version": report.claim_set.version,
            "incident_id": report.claim_set.incident_id,
            "cases": report.case_count,
        },
        "judge": _selection_payload(judge),
        "semantic_error": semantic_error,
        "summary": {
            "deterministic_correct": report.deterministic_correct_count,
            "deterministic_accuracy": report.deterministic_accuracy,
            "final_correct": report.final_correct_count,
            "final_accuracy": report.final_accuracy,
            "semantic_evaluated": report.semantic_evaluated_count,
            "disagreements": report.disagreement_count,
            "corrected_by_semantic": report.corrected_count,
            "regressed_by_semantic": report.regressed_count,
            "false_upgrades": report.false_upgrade_count,
            "false_rejections": report.false_rejection_count,
            "authority_false_positives": report.authority_false_positive_count,
            "semantic_model_calls": report.semantic_model_calls,
            "semantic_input_tokens": report.semantic_usage.input_tokens,
            "semantic_output_tokens": report.semantic_usage.output_tokens,
        },
        "rows": rows,
    }


def _print_human(
    report: ClaimMatrixReport,
    *,
    judge: ProviderSelection | None,
    semantic_error: str | None = None,
) -> None:
    print(
        f"claim set: {report.claim_set.name} {report.claim_set.version} "
        f"({report.case_count} cases, {report.claim_set.incident_id})"
    )
    print(
        f"deterministic: {report.deterministic_correct_count}/{report.case_count} "
        f"({report.deterministic_accuracy:.1%})"
    )
    print(
        f"final:         {report.final_correct_count}/{report.case_count} "
        f"({report.final_accuracy:.1%})"
    )
    if judge is not None:
        print(f"judge:         {judge.provider} / {judge.model}")
        print(
            f"semantic:      {report.semantic_evaluated_count} evaluated, "
            f"{report.disagreement_count} disagreements, {report.semantic_model_calls} calls"
        )
    if semantic_error is not None:
        print(f"semantic error: {semantic_error}", file=sys.stderr)

    print("case | expected | deterministic | semantic | final | correct")
    for row in report.rows:
        semantic = row.semantic_kind.value if row.semantic_kind is not None else "-"
        correct = "yes" if row.final_correct else "NO"
        print(
            f"{row.case_id} | {row.expected_kind.value} | {row.deterministic_kind.value} | "
            f"{semantic} | {row.final_kind.value} | {correct}"
        )


def _render(
    report: ClaimMatrixReport,
    *,
    judge: ProviderSelection | None,
    semantic_error: str | None,
    json_output: bool,
) -> None:
    if json_output:
        print(
            json.dumps(
                _report_payload(report, judge=judge, semantic_error=semantic_error),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    _print_human(report, judge=judge, semantic_error=semantic_error)


def main(argv: list[str] | None = None) -> int:
    """Run the static claim matrix and optionally invoke an independent semantic judge."""
    args = parse_args(argv)
    try:
        claim_set = load_labelled_claims_v1()
        store = InMemoryIncidentStore()
        incident = store.get_incident(claim_set.incident_id)
        evidence = store.get_evidence(incident)
        baseline = ClaimJudgeMatrixRunner().evaluate(
            claim_set=claim_set,
            incident=incident,
            evidence=evidence,
        )
    except (LabelledClaimSetError, ClaimMatrixError) as exc:
        print(f"claim matrix failed: {exc}", file=sys.stderr)
        return 2

    if not args.semantic:
        _render(
            baseline,
            judge=None,
            semantic_error=None,
            json_output=bool(args.json),
        )
        return 0

    try:
        judge_client, judge_selection = semantic_client_from_env()
    except SystemExit as exc:
        _render(
            baseline,
            judge=None,
            semantic_error=str(exc),
            json_output=bool(args.json),
        )
        return 2

    try:
        report = ClaimJudgeMatrixRunner(
            semantic=SemanticClaimEvaluatorV21(model=judge_client)
        ).evaluate(
            claim_set=claim_set,
            incident=incident,
            evidence=evidence,
        )
    except (ModelProviderError, SemanticClaimEvaluationError, ClaimMatrixError) as exc:
        _render(
            baseline,
            judge=judge_selection,
            semantic_error=str(exc),
            json_output=bool(args.json),
        )
        return 2

    _render(
        report,
        judge=judge_selection,
        semantic_error=None,
        json_output=bool(args.json),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
