"""Cross-model semantic claim calibration without changing benchmark semantics."""

import argparse
import json
import sys
from collections.abc import Sequence

import autonomy_lab.cli as base_cli
from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.adapters.providers import (
    ProviderSelection,
    configured_client_from_env,
    semantic_client_from_env,
)
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.application.grounding import DeterministicGroundingEvaluator
from autonomy_lab.application.model_errors import ModelProviderError, ModelRateLimitError
from autonomy_lab.application.semantic_claim_evaluation import (
    SemanticClaimEvaluationError,
    SemanticClaimEvaluatorV21,
)
from autonomy_lab.domain.autonomy import AutonomyPattern


def _selection_payload(selection: ProviderSelection) -> dict[str, object]:
    return {
        "provider": selection.provider,
        "model": selection.model,
        "max_tokens": selection.max_tokens,
        "timeout_seconds": selection.timeout_seconds,
    }


def _same_model(left: ProviderSelection, right: ProviderSelection) -> bool:
    return left.provider == right.provider and left.model == right.model


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semantic-judge-calibration",
        description="Run one pattern and evaluate conservative claim misses with a separate judge.",
    )
    parser.add_argument("pattern", choices=[pattern.value for pattern in AutonomyPattern])
    parser.add_argument("--incident", default="INC-001")
    parser.add_argument("--json", action="store_true")
    return parser


def _print_payload(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"pattern:   {payload['pattern']}")
    generator = payload["generator"]
    judge = payload.get("judge")
    print(f"generator: {generator}")
    print(f"judge:     {judge}")
    print(f"self-judge:{' yes' if payload.get('self_judge') else ' no'}")
    semantic = payload["semantic_claim_evaluation"]
    print(f"semantic:  {semantic}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one generator/judge calibration and keep judge usage separate."""
    args = _parser().parse_args(argv)
    store = InMemoryIncidentStore()
    generator, generator_selection = configured_client_from_env()
    pattern = AutonomyPattern(args.pattern)

    try:
        run = base_cli._build_runner(pattern, store=store, model=generator).run(args.incident)
    except ModelRateLimitError as exc:
        return base_cli._print_run_failure(
            pattern=pattern,
            incident_id=args.incident,
            status="rate_limited",
            error=exc,
            as_json=args.json,
        )
    except ModelProviderError as exc:
        return base_cli._print_run_failure(
            pattern=pattern,
            incident_id=args.incident,
            status="provider_error",
            error=exc,
            as_json=args.json,
        )

    grounding = base_cli._grounding_for_run(
        run,
        store=store,
        evaluator=DeterministicGroundingEvaluator(),
    )
    deterministic = base_cli._claim_evaluation_for_run(
        run,
        store=store,
        evaluator=DeterministicClaimEvaluatorV2(),
    )

    try:
        judge, judge_selection = semantic_client_from_env()
    except SystemExit as exc:
        payload = base_cli._run_payload(
            run,
            grounding,
            deterministic,
            semantic_error=f"configuration_error: {exc}",
        )
        payload["generator"] = _selection_payload(generator_selection)
        payload["judge"] = None
        payload["self_judge"] = False
        _print_payload(payload, as_json=args.json)
        return 2

    semantic_error: str | None = None
    merged = None
    incident = store.get_incident(run.incident_id)
    evidence = store.get_evidence(incident)
    try:
        merged = SemanticClaimEvaluatorV21(model=judge).evaluate(
            deterministic=deterministic,
            evidence=evidence,
        )
    except ModelRateLimitError as exc:
        semantic_error = f"rate_limited: {exc}"
    except ModelProviderError as exc:
        semantic_error = f"provider_error: {exc}"
    except SemanticClaimEvaluationError as exc:
        semantic_error = f"invalid_semantic_output: {exc}"

    payload = base_cli._run_payload(
        run,
        grounding,
        deterministic,
        merged,
        semantic_error,
    )
    payload["generator"] = _selection_payload(generator_selection)
    payload["judge"] = _selection_payload(judge_selection)
    payload["self_judge"] = _same_model(generator_selection, judge_selection)
    _print_payload(payload, as_json=args.json)
    return 2 if semantic_error is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
