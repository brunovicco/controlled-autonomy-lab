from harness_example.application.comparison import repeat_pattern, summarize_repetitions
from harness_example.domain.autonomy import AutonomyPattern, ModelUsage, PatternRun


class SequenceRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, incident_id: str) -> PatternRun:
        self.calls += 1
        steps = ("tool-a", "final-answer") if self.calls < 3 else ("tool-b", "final-answer")
        return PatternRun(
            pattern=AutonomyPattern.AGENT,
            incident_id=incident_id,
            answer="answer",
            model_calls=2,
            tool_calls=1,
            steps=steps,
            usage=ModelUsage(10, 2),
            latency_ms=1.0,
        )


def test_repetition_summary_counts_unique_trajectories() -> None:
    results = repeat_pattern(SequenceRunner(), incident_id="INC-001", runs=3)
    summary = summarize_repetitions(results)

    assert summary.pattern is AutonomyPattern.AGENT
    assert summary.runs == 3
    assert summary.unique_trajectories == 2
