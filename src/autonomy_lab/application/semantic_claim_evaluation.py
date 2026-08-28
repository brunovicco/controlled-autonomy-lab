"""Secondary semantic claim evaluator with deterministic-authoritative merge policy."""

import json
from collections.abc import Mapping
from typing import Any

from autonomy_lab.application.ports import TextModel
from autonomy_lab.domain.autonomy import EvidenceItem, ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimEvaluation, ClaimEvaluationReport, ClaimKind
from autonomy_lab.domain.semantic_claim_evaluation import (
    MergedClaimEvaluation,
    MergedClaimEvaluationReport,
    SemanticClaimJudgement,
    SemanticClaimVerdict,
)

_SYSTEM = """You are a bounded semantic support classifier.
Evaluate exactly one claim using only the supplied evidence summaries.
Do not use outside knowledge.
Return exactly one JSON object and no Markdown or explanatory text.

Schema fields:
- verdict: supported-fact, supported-inference, or unsupported-claim
- rationale: short reason
- evidence_sources: list of supplied source ids

Rules:
- supported-fact: evidence directly states or semantically entails the claim.
- supported-inference: the claim is explicitly qualified as an inference or hypothesis,
  and the evidence reasonably supports it without asserting causality as fact.
- unsupported-claim: evidence is insufficient, contradictory, or needs outside knowledge.
- Historical evidence may support a statement about that historical incident, but it must
  never establish the current incident's root cause.
- evidence_sources must contain only supplied ids that materially support the verdict.
"""


class SemanticClaimEvaluationError(ValueError):
    """Raised when a semantic evaluator response violates the bounded JSON contract."""


def _is_hard_failure(claim: ClaimEvaluation) -> bool:
    if claim.kind is not ClaimKind.UNSUPPORTED_CLAIM:
        return False
    return claim.rationale.startswith(("grounding-v1-", "deterministic-authority-"))


def _is_semantic_candidate(claim: ClaimEvaluation) -> bool:
    return claim.kind is ClaimKind.UNSUPPORTED_CLAIM and not _is_hard_failure(claim)


def _prompt_for(claim: str, evidence: tuple[EvidenceItem, ...]) -> str:
    payload = {
        "claim": claim,
        "evidence": [{"source": item.source, "summary": item.summary} for item in evidence],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse_judgement(
    *,
    claim: str,
    raw: str,
    allowed_sources: frozenset[str],
) -> SemanticClaimJudgement:
    try:
        decoded: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SemanticClaimEvaluationError("semantic evaluator returned invalid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise SemanticClaimEvaluationError("semantic evaluator response must be a JSON object")
    if set(decoded) != {"verdict", "rationale", "evidence_sources"}:
        raise SemanticClaimEvaluationError("semantic evaluator response has unexpected fields")

    verdict_raw = decoded.get("verdict")
    rationale = decoded.get("rationale")
    sources_raw = decoded.get("evidence_sources")
    if not isinstance(verdict_raw, str):
        raise SemanticClaimEvaluationError("semantic verdict must be a string")
    try:
        verdict = SemanticClaimVerdict(verdict_raw)
    except ValueError as exc:
        raise SemanticClaimEvaluationError("semantic verdict is not allowed") from exc
    if not isinstance(rationale, str) or not rationale.strip():
        raise SemanticClaimEvaluationError("semantic rationale must be a non-empty string")
    rationale = " ".join(rationale.split())
    if len(rationale) > 240:
        raise SemanticClaimEvaluationError("semantic rationale exceeds 240 characters")
    if not isinstance(sources_raw, list) or any(
        not isinstance(source, str) for source in sources_raw
    ):
        raise SemanticClaimEvaluationError("semantic evidence_sources must be a string list")
    sources = tuple(dict.fromkeys(sources_raw))
    if any(source not in allowed_sources for source in sources):
        raise SemanticClaimEvaluationError("semantic evaluator returned an unknown evidence source")
    if verdict is not SemanticClaimVerdict.UNSUPPORTED_CLAIM and not sources:
        raise SemanticClaimEvaluationError("supported semantic verdict requires evidence_sources")

    return SemanticClaimJudgement(
        claim=claim,
        verdict=verdict,
        rationale=rationale,
        evidence_sources=sources,
    )


def _merge_without_semantic(claim: ClaimEvaluation) -> MergedClaimEvaluation:
    if _is_hard_failure(claim):
        resolution = "deterministic-hard-failure"
    else:
        resolution = "deterministic-authoritative"
    return MergedClaimEvaluation(
        deterministic=claim,
        semantic=None,
        final_kind=claim.kind,
        disagreement=False,
        resolution=resolution,
    )


def _merge_with_semantic(
    deterministic: ClaimEvaluation,
    semantic: SemanticClaimJudgement,
) -> MergedClaimEvaluation:
    final_kind = semantic.verdict.claim_kind
    disagreement = final_kind is not deterministic.kind
    resolution = "semantic-upgrade" if disagreement else "semantic-confirmed-unsupported"
    return MergedClaimEvaluation(
        deterministic=deterministic,
        semantic=semantic,
        final_kind=final_kind,
        disagreement=disagreement,
        resolution=resolution,
    )


class SemanticClaimEvaluatorV21:
    """Evaluate only conservative deterministic misses and merge without weakening hard signals."""

    def __init__(self, *, model: TextModel) -> None:
        """Configure the provider-neutral semantic model dependency."""
        self._model = model

    def evaluate(
        self,
        *,
        deterministic: ClaimEvaluationReport,
        evidence: tuple[EvidenceItem, ...],
    ) -> MergedClaimEvaluationReport:
        """Return deterministic + semantic + final results with separate model-call accounting."""
        allowed_sources = frozenset(item.source for item in evidence)
        merged: list[MergedClaimEvaluation] = []
        model_calls = 0
        usage = ModelUsage()

        for claim in deterministic.claims:
            if not _is_semantic_candidate(claim):
                merged.append(_merge_without_semantic(claim))
                continue

            turn = self._model.complete(
                system=_SYSTEM,
                prompt=_prompt_for(claim.claim, evidence),
            )
            model_calls += 1
            usage += turn.usage
            semantic = _parse_judgement(
                claim=claim.claim,
                raw=turn.text.strip(),
                allowed_sources=allowed_sources,
            )
            merged.append(_merge_with_semantic(claim, semantic))

        return MergedClaimEvaluationReport(
            claims=tuple(merged),
            semantic_model_calls=model_calls,
            semantic_usage=usage,
        )
