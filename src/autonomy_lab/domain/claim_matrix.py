"""Domain contracts for static human-labelled claim evaluation."""

from dataclasses import dataclass, field

from autonomy_lab.domain.autonomy import ModelUsage
from autonomy_lab.domain.claim_evaluation import ClaimKind


@dataclass(frozen=True, slots=True)
class LabelledClaimCase:
    """One human-labelled claim example with bounded evaluation context."""

    case_id: str
    category: str
    answer: str
    expected_kind: ClaimKind
    notes: str = ""


@dataclass(frozen=True, slots=True)
class LabelledClaimSet:
    """Versioned static claim set bound to one incident fixture."""

    name: str
    version: str
    incident_id: str
    cases: tuple[LabelledClaimCase, ...]


@dataclass(frozen=True, slots=True)
class ClaimMatrixRow:
    """Human label, deterministic result, and optional semantic result for one case."""

    case_id: str
    category: str
    claim: str
    expected_kind: ClaimKind
    deterministic_kind: ClaimKind
    deterministic_rationale: str
    semantic_kind: ClaimKind | None
    final_kind: ClaimKind
    semantic_evaluated: bool
    disagreement: bool
    resolution: str

    @property
    def deterministic_correct(self) -> bool:
        """Return whether the deterministic prediction matches the human label."""
        return self.deterministic_kind is self.expected_kind

    @property
    def final_correct(self) -> bool:
        """Return whether the final merged prediction matches the human label."""
        return self.final_kind is self.expected_kind

    @property
    def corrected_by_semantic(self) -> bool:
        """Return whether semantic evaluation corrected a deterministic miss."""
        return not self.deterministic_correct and self.final_correct

    @property
    def regressed_by_semantic(self) -> bool:
        """Return whether semantic evaluation changed a correct result into an error."""
        return self.deterministic_correct and not self.final_correct


@dataclass(frozen=True, slots=True)
class ClaimMatrixReport:
    """Aggregate deterministic and optional semantic evaluation over a labelled set."""

    claim_set: LabelledClaimSet
    rows: tuple[ClaimMatrixRow, ...]
    semantic_model_calls: int = 0
    semantic_usage: ModelUsage = field(default_factory=ModelUsage)

    @property
    def case_count(self) -> int:
        """Return the number of labelled cases."""
        return len(self.rows)

    @property
    def deterministic_correct_count(self) -> int:
        """Return deterministic exact-label matches."""
        return sum(row.deterministic_correct for row in self.rows)

    @property
    def deterministic_accuracy(self) -> float:
        """Return deterministic exact-label accuracy."""
        return self._ratio(self.deterministic_correct_count)

    @property
    def final_correct_count(self) -> int:
        """Return final exact-label matches after optional semantic merge."""
        return sum(row.final_correct for row in self.rows)

    @property
    def final_accuracy(self) -> float:
        """Return final exact-label accuracy after optional semantic merge."""
        return self._ratio(self.final_correct_count)

    @property
    def semantic_evaluated_count(self) -> int:
        """Return the number of cases actually sent to a semantic judge."""
        return sum(row.semantic_evaluated for row in self.rows)

    @property
    def disagreement_count(self) -> int:
        """Return deterministic-versus-semantic disagreements."""
        return sum(row.disagreement for row in self.rows)

    @property
    def corrected_count(self) -> int:
        """Return deterministic misses corrected by semantic evaluation."""
        return sum(row.corrected_by_semantic for row in self.rows)

    @property
    def regressed_count(self) -> int:
        """Return deterministic matches made incorrect by semantic evaluation."""
        return sum(row.regressed_by_semantic for row in self.rows)

    @property
    def false_upgrade_count(self) -> int:
        """Return unsupported human labels incorrectly upgraded to supported final kinds."""
        supported = {ClaimKind.SUPPORTED_FACT, ClaimKind.SUPPORTED_INFERENCE}
        return sum(
            row.expected_kind is ClaimKind.UNSUPPORTED_CLAIM and row.final_kind in supported
            for row in self.rows
        )

    @property
    def false_rejection_count(self) -> int:
        """Return supported human labels that remain unsupported after final merge."""
        supported = {ClaimKind.SUPPORTED_FACT, ClaimKind.SUPPORTED_INFERENCE}
        return sum(
            row.expected_kind in supported and row.final_kind is ClaimKind.UNSUPPORTED_CLAIM
            for row in self.rows
        )

    @property
    def authority_false_positive_count(self) -> int:
        """Return deterministic supported results that disagree with the human label.

        These rows are important because the current authority policy does not send already-supported
        deterministic claims to the semantic judge.
        """
        supported = {ClaimKind.SUPPORTED_FACT, ClaimKind.SUPPORTED_INFERENCE}
        return sum(
            row.deterministic_kind in supported and not row.deterministic_correct for row in self.rows
        )

    def _ratio(self, count: int) -> float:
        if not self.rows:
            return 1.0
        return count / len(self.rows)
