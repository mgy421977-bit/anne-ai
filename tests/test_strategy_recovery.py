from anne.learning.experience_learning import Experience
from anne.learning.strategy_recovery import (
    StrategyRecoveryAction,
    StrategyRecoveryEvaluator,
)


def _experience(
    cycle_id: str,
    strategy: str,
    outcome: str,
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class="evidence_gap" if outcome == "FAILURE" else "unknown",
        strategy=strategy,
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
    )


def test_repeated_failure_of_changed_strategy_requests_bounded_rollback() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE"),
        _experience("c2", "recheck_independent_evidence", "FAILURE"),
        _experience("c3", "recheck_independent_evidence", "FAILURE"),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.ROLLBACK
    assert result.strategy == "research"
    assert result.source_cycle_ids == ("c2", "c3")


def test_single_failure_does_not_trigger_rollback() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE"),
        _experience("c2", "recheck_independent_evidence", "FAILURE"),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.INSUFFICIENT_OBSERVATION


def test_successful_changed_strategy_is_kept() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE"),
        _experience("c2", "recheck_independent_evidence", "SUCCESS"),
        _experience("c3", "recheck_independent_evidence", "SUCCESS"),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.KEEP


def test_rollback_requires_prior_observed_strategy() -> None:
    experiences = (
        _experience("c1", "recheck_independent_evidence", "FAILURE"),
        _experience("c2", "recheck_independent_evidence", "FAILURE"),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.ABSTAIN
    assert result.strategy == "reassess_without_assuming_cause"
