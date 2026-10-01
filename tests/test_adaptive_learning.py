"""Tests for the bounded adaptive learning coordinator."""

from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.learning.experience_learning import Experience
from anne.learning.strategy_recovery import StrategyRecoveryAction


def _experience(
    cycle_id: str,
    strategy: str,
    outcome: str,
    *,
    context_key: str = "",
    context_conditions: tuple[tuple[str, str], ...] = (),
    parent_cycle_id: str | None = None,
    lineage: tuple[str, ...] = (),
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class="evidence_gap",
        strategy=strategy,
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context_key,
        context_conditions=context_conditions,
        parent_cycle_id=parent_cycle_id,
        lineage=lineage,
    )


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


def test_adaptive_learning_can_observe_bounded_rollback_need() -> None:
    trace = CycleTrace(
        cycle_id="c13",
        status="BOUNDED",
        stop_reason="evidence_gap",
        verification={"status": "UNVERIFIED"},
        learning={"context": {"key": "web_research", "conditions": {"source_count": 2}}},
        lineage=("c11", "c12", "c13"),
    )
    prior = (
        _experience("c11", "research", "FAILURE", context_key="web_research", context_conditions=(("source_count", "2"),), lineage=("c11",)),
        _experience("c12", "recheck_independent_evidence", "FAILURE", context_key="web_research", context_conditions=(("source_count", "2"),), lineage=("c11", "c12")),
    )

    result = AdaptiveLearningCoordinator().observe(
        trace,
        strategy="recheck_independent_evidence",
        prior_experiences=prior,
    )

    assert result.strategy_recovery.action is StrategyRecoveryAction.ROLLBACK
    assert result.strategy_recovery.strategy == "research"
    assert result.trace.learning["strategy_recovery"]["action"] == "rollback"


def test_adaptive_learning_uses_exact_context_observations_for_strategy_choice() -> None:
    def experience(cycle_id: str, strategy: str, outcome: str) -> Experience:
        return Experience(
            source_cycle_id=cycle_id,
            outcome=outcome,
            failure_class="evidence_gap",
            strategy=strategy,
            lesson="observation only",
            safe_to_reuse=False,
            factual_status="UNVERIFIED",
            context_key="web_research",
            context_conditions=(("freshness", "current"), ("source_count", "2")),
        )

    trace = CycleTrace(
        cycle_id="c20",
        status="BOUNDED",
        stop_reason="evidence_gap",
        learning={
            "context": {
                "key": "web_research",
                "conditions": {"source_count": 2, "freshness": "current"},
            }
        },
    )
    prior = (
        experience("c18", "research", "FAILURE"),
        experience("c19", "research", "FAILURE"),
        experience("c17", "recheck_independent_evidence", "SUCCESS"),
    )

    result = AdaptiveLearningCoordinator().observe(
        trace,
        strategy="research",
        prior_experiences=prior,
    )

    assert result.strategy.action == "CHANGE"
    assert result.strategy.strategy == "recheck_independent_evidence"
    assert result.trace.learning["contextual_strategy"]["selected_by_observation"] is True


def test_adaptive_learning_does_not_reuse_missing_context() -> None:
    trace = CycleTrace(
        cycle_id="c21",
        status="BOUNDED",
        stop_reason="evidence_gap",
    )
    prior = (
        _experience("c18", "research", "FAILURE"),
        _experience("c19", "research", "FAILURE"),
    )

    result = AdaptiveLearningCoordinator().observe(
        trace,
        strategy="research",
        prior_experiences=prior,
    )

    assert result.strategy.action == "CHANGE"
    assert result.strategy.strategy == "seek_fresh_independent_evidence"
    assert result.trace.learning["contextual_strategy"]["selected_by_observation"] is False
