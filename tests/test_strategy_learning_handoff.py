from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.learning.contextual_strategy import StrategyContext
from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyAdapter


def _experience(cycle_id: str, outcome: str, failure_class: str, strategy: str, context_key: str) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class=failure_class,
        strategy=strategy,
        lesson="synthetic",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context_key,
    )


def test_same_context_carries_observed_strategy_to_next_cycle() -> None:
    history = (
        _experience("c1", "FAILURE", "evidence_gap", "research", "task-a"),
        _experience("c2", "FAILURE", "evidence_gap", "research", "task-a"),
        _experience("c3", "SUCCESS", "unknown", "seek_fresh_independent_evidence", "task-a"),
    )
    decision = StrategyAdapter().adapt("seek_fresh_independent_evidence", history)
    choice = AdaptiveLearningCoordinator().contextual_selector.select(
        StrategyContext("unknown", "task-a"),
        history,
        ("seek_fresh_independent_evidence", "research"),
    )
    assert decision.action == "KEEP"
    assert choice.strategy == "seek_fresh_independent_evidence"
    assert choice.selected_by_observation is True


def test_different_context_does_not_import_successful_strategy() -> None:
    history = (
        _experience("c1", "SUCCESS", "unknown", "seek_fresh_independent_evidence", "task-a"),
    )
    choice = AdaptiveLearningCoordinator().contextual_selector.select(
        StrategyContext("unknown", "task-b"),
        history,
        ("research", "seek_fresh_independent_evidence"),
    )
    assert choice.strategy == "research"
    assert choice.selected_by_observation is False


def test_safety_failure_stays_authority_bound() -> None:
    history = (
        _experience("c1", "FAILURE", "execution_risk", "execute", "task-c"),
        _experience("c2", "FAILURE", "execution_risk", "execute", "task-c"),
    )
    decision = StrategyAdapter().adapt("execute", history)
    assert decision.action == "ABSTAIN"
    assert decision.strategy == "require_authority_review"
