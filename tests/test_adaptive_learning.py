"""Tests for the bounded adaptive learning coordinator."""

from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator


def test_adaptive_learning_keeps_strategy_after_one_evidence_gap() -> None:
    trace = CycleTrace(
        cycle_id="c10",
        status="BOUNDED",
        stop_reason="evidence_gap",
        verification={"status": "UNVERIFIED"},
        decision={"status": "INSUFFICIENT_EVIDENCE"},
    )
    result = AdaptiveLearningCoordinator().observe(trace, strategy="answer_directly")
    assert result.information_gap.present is True
    assert result.strategy.action == "KEEP"
    assert result.strategy.strategy == "answer_directly"


def test_adaptive_learning_does_not_change_after_one_failure() -> None:
    trace = CycleTrace(
        cycle_id="c11",
        status="BOUNDED",
        stop_reason="evidence_gap",
        verification={"status": "UNVERIFIED"},
    )
    result = AdaptiveLearningCoordinator().observe(trace, strategy="answer_directly")
    assert result.strategy.action == "KEEP"


def test_adaptive_learning_preserves_execution_boundary() -> None:
    trace = CycleTrace(
        cycle_id="c12",
        status="BOUNDED",
        stop_reason="execution_risk",
    )
    result = AdaptiveLearningCoordinator().observe(trace, strategy="execute")
    assert result.strategy.action == "ABSTAIN"
    assert result.strategy.strategy == "require_authority_review"
