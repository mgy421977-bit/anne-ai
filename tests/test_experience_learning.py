"""Tests for bounded information-gap detection and experience-driven adaptation."""

from anne.core.trace import CycleTrace
from anne.learning.experience_learning import ExperienceLearner
from anne.learning.information_gap import InformationGapDetector
from anne.learning.strategy_adaptation import StrategyAdapter


def _trace(
    *,
    cycle_id: str,
    status: str = "BOUNDED",
    stop_reason: str = "",
    verification: dict | None = None,
    decision: dict | None = None,
    errors: tuple[dict, ...] = (),
) -> CycleTrace:
    return CycleTrace(
        cycle_id=cycle_id,
        status=status,
        stage_trace=("FAIL_FAST", "DUY", "BAK"),
        stop_reason=stop_reason,
        verification=verification or {},
        decision=decision or {},
        errors=errors,
    )


def test_information_gap_detects_unverified_evidence() -> None:
    trace = _trace(
        cycle_id="c1",
        verification={"status": "UNVERIFIED"},
        decision={"status": "INSUFFICIENT_EVIDENCE"},
    )
    gap = InformationGapDetector().detect(trace)
    assert gap.present is True
    assert "evidence" in gap.categories


def test_information_gap_does_not_treat_confidence_as_evidence() -> None:
    trace = _trace(
        cycle_id="c2",
        verification={"status": "UNVERIFIED", "confidence": 0.99},
        decision={"status": "SUPPORTED"},
    )
    gap = InformationGapDetector().detect(trace)
    assert gap.present is True


def test_experience_learning_extracts_failure_without_upgrading_truth() -> None:
    trace = _trace(
        cycle_id="c3",
        stop_reason="evidence_gap",
        errors=({"stage": "ANLA", "reason": "fresh evidence required"},),
    )
    experience = ExperienceLearner().from_trace(trace, strategy="answer_directly")
    assert experience.outcome == "FAILURE"
    assert experience.failure_class == "evidence_gap"
    assert experience.safe_to_reuse is False
    assert experience.source_cycle_id == "c3"


def test_strategy_changes_after_repeated_same_failure() -> None:
    learner = ExperienceLearner()
    traces = [
        _trace(cycle_id="c4", stop_reason="evidence_gap"),
        _trace(cycle_id="c5", stop_reason="evidence_gap"),
    ]
    experiences = tuple(
        learner.from_trace(t, strategy="answer_directly") for t in traces
    )
    decision = StrategyAdapter().adapt("answer_directly", experiences)
    assert decision.action == "CHANGE"
    assert decision.strategy == "seek_fresh_independent_evidence"


def test_strategy_abstains_on_execution_risk() -> None:
    learner = ExperienceLearner()
    experience = learner.from_trace(
        _trace(cycle_id="c6", stop_reason="execution_risk"),
        strategy="execute",
    )
    decision = StrategyAdapter().adapt("execute", (experience,))
    assert decision.action == "ABSTAIN"
    assert decision.strategy == "require_authority_review"
