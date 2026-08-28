from autonomy_lab.adapters.incidents import InMemoryIncidentStore
from autonomy_lab.application.claim_evaluation import DeterministicClaimEvaluatorV2
from autonomy_lab.domain.claim_evaluation import ClaimEvaluationReport, ClaimKind


def _evaluate(incident_id: str, answer: str) -> ClaimEvaluationReport:
    store = InMemoryIncidentStore()
    incident = store.get_incident(incident_id)
    return DeterministicClaimEvaluatorV2().evaluate(
        answer=answer,
        incident=incident,
        evidence=store.get_evidence(incident),
    )


def test_inc002_structural_intro_is_not_counted_as_claim() -> None:
    answer = "This is one of the stronger cases — causality is established, not just correlated:"

    report = _evaluate("INC-002", answer)

    assert report.claims == ()


def test_inc002_provider_outage_exclusion_is_supported_inference() -> None:
    answer = (
        "This is important because it eliminates third-party outage as an alternative explanation."
    )

    report = _evaluate("INC-002", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "dependencies" in report.claims[0].evidence_sources


def test_inc002_review_meta_statement_is_proposed_action() -> None:
    answer = "That's a process gap worth reviewing but doesn't change the technical root cause."

    report = _evaluate("INC-002", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.PROPOSED_ACTION


def test_inc002_historical_irrelevance_is_supported_inference() -> None:
    answer = (
        "No unrelated prior incidents (INC-901, cache-header issue) apply here — "
        "confirmed separate and irrelevant to this root cause."
    )

    report = _evaluate("INC-002", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "previous-incidents" in report.claims[0].evidence_sources


def test_inc003_local_regression_exclusion_is_supported_inference() -> None:
    report = _evaluate("INC-003", "Rules out a local code/config regression.")

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "deployments" in report.claims[0].evidence_sources


def test_inc003_unrelated_previous_incident_is_supported_inference() -> None:
    answer = "Previous incidents: INC-744 is unrelated and explicitly not applicable here."

    report = _evaluate("INC-003", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "previous-incidents" in report.claims[0].evidence_sources


def test_inc003_runbook_methodology_is_supported_inference() -> None:
    answer = (
        "Runbook: Notes that provider-confirmed incident + aligned failure/recovery timing + "
        "absence of local changes is the standard bar for establishing dependency-caused failure."
    )

    report = _evaluate("INC-003", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "runbook" in report.claims[0].evidence_sources


def test_inc003_reported_root_cause_caveat_is_supported_inference() -> None:
    answer = (
        "Caveat on causality: This is strong correlational evidence, reinforced by the dependency "
        "tool's explicit statement that root cause is confirmed."
    )

    report = _evaluate("INC-003", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE


def test_inc003_reported_confirmation_attribution_is_supported_inference() -> None:
    answer = (
        "I'm treating root cause confirmed as reported by the dependency system, not as "
        "independently re-derived from raw logs."
    )

    report = _evaluate("INC-003", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "dependencies" in report.claims[0].evidence_sources


def test_inc003_no_further_action_statement_is_proposed_action() -> None:
    report = _evaluate(
        "INC-003",
        "No further immediate action required beyond monitoring and log verification above.",
    )

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.PROPOSED_ACTION


def test_inc004_bold_abstention_is_supported_inference() -> None:
    answer = (
        "**No causal conclusion should be drawn yet** — recommend gathering traces + resource "
        "data before attributing root cause."
    )

    report = _evaluate("INC-004", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.SUPPORTED_INFERENCE
    assert "runbook" in report.claims[0].evidence_sources


def test_inc004_historical_paraphrase_remains_conservative_miss() -> None:
    answer = (
        "A prior incident (INC-655) had similar latency signature under memory pressure — "
        "historical pattern match only, not evidence for this incident."
    )

    report = _evaluate("INC-004", answer)

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM


def test_inc004_context_dependent_fragment_remains_unsupported() -> None:
    report = _evaluate("INC-004", "Could be a partial trigger or coincidental.")

    assert len(report.claims) == 1
    assert report.claims[0].kind is ClaimKind.UNSUPPORTED_CLAIM
    assert report.claims[0].rationale == "inference-without-evidence-anchor"
