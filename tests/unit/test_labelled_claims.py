from collections import Counter

from autonomy_lab.adapters.labelled_claims import load_labelled_claims_v1
from autonomy_lab.domain.claim_evaluation import ClaimKind


def test_labelled_claim_set_v1_has_balanced_static_cases() -> None:
    claim_set = load_labelled_claims_v1()

    assert claim_set.name == "inc-001-claim-calibration"
    assert claim_set.version == "v1"
    assert claim_set.incident_id == "INC-001"
    assert len(claim_set.cases) == 18
    assert len({case.case_id for case in claim_set.cases}) == 18

    counts = Counter(case.expected_kind for case in claim_set.cases)
    assert counts == {
        ClaimKind.SUPPORTED_FACT: 5,
        ClaimKind.SUPPORTED_INFERENCE: 2,
        ClaimKind.PROPOSED_ACTION: 3,
        ClaimKind.UNSUPPORTED_CLAIM: 8,
    }
