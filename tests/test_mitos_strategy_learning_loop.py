"""Regression tests for the bounded MITOS -> strategy-learning handoff."""

from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.mythos.experience import ExperienceRecord, ExperienceStatus


def _failed_trace(context: dict[str, object]) -> CycleTrace:
    return CycleTrace(
        cycle_id="current-cycle",
        status="FAILED",
        stop_reason="evidence_gap",
        intent={"requires_evidence": True},
        learning={
            "context": {
                "key": "mitos",
                "conditions": context,
            }
        },
    )


def _failed_mitos(hypothesis_id: str, context: dict[str, object]) -> ExperienceRecord:
    return ExperienceRecord(
        hypothesis_id=hypothesis_id,
        goal="bounded test",
        claim="synthetic claim",
        status=ExperienceStatus.FAILED,
        context=context,
    )


def test_repeated_mitos_failures_change_strategy_in_exact_context() -> None:
    result = AdaptiveLearningCoordinator().observe(
        _failed_trace({"mode": "research"}),
        strategy="bounded_test",
        mitos_outcomes=(
            _failed_mitos("m1", {"mode": "research"}),
            _failed_mitos("m2", {"mode": "research"}),
        ),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert result.strategy.action == "CHANGE"
    assert result.strategy.strategy == "seek_fresh_independent_evidence"
    assert result.strategy.source_cycle_ids == ("m1", "m2", "current-cycle")


def test_repeated_mitos_failures_in_other_context_do_not_change_strategy() -> None:
    result = AdaptiveLearningCoordinator().observe(
        _failed_trace({"mode": "research"}),
        strategy="bounded_test",
        mitos_outcomes=(
            _failed_mitos("m1", {"mode": "production"}),
            _failed_mitos("m2", {"mode": "production"}),
        ),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert result.strategy.action == "KEEP"
    assert result.strategy.strategy == "bounded_test"
    assert result.strategy.source_cycle_ids == ("current-cycle",)
