from anne.learning.experience_learning import Experience
from anne.learning.strategy_recovery import (
    StrategyRecoveryAction,
    StrategyRecoveryEvaluator,
)


def _experience(
    cycle_id: str,
    strategy: str,
    outcome: str,
    *,
    context_key: str = "",
    parent_cycle_id: str | None = None,
    lineage: tuple[str, ...] = (),
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class="evidence_gap" if outcome == "FAILURE" else "unknown",
        strategy=strategy,
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context_key,
        parent_cycle_id=parent_cycle_id,
        lineage=lineage,
    )


def test_repeated_failure_of_changed_strategy_requests_bounded_rollback() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE", context_key="web"),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("c1",),
        ),
        _experience(
            "c3",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c2",
            lineage=("c1", "c2"),
        ),
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
        _experience("c1", "research", "FAILURE", context_key="web"),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("c1",),
        ),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.INSUFFICIENT_OBSERVATION


def test_successful_changed_strategy_is_kept() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE", context_key="web"),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "SUCCESS",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("c1",),
        ),
        _experience(
            "c3",
            "recheck_independent_evidence",
            "SUCCESS",
            context_key="web",
            parent_cycle_id="c2",
            lineage=("c1", "c2"),
        ),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.KEEP


def test_rollback_requires_prior_observed_strategy() -> None:
    experiences = (
        _experience(
            "c1",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
        ),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("c1",),
        ),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.ABSTAIN
    assert result.strategy == "reassess_without_assuming_cause"


def test_unrelated_context_does_not_trigger_rollback() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE", context_key="web"),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("c1",),
        ),
        _experience(
            "c3",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="mobile",
            parent_cycle_id="c2",
            lineage=("c1", "c2"),
        ),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.INSUFFICIENT_OBSERVATION


def test_unrelated_lineage_does_not_trigger_rollback() -> None:
    experiences = (
        _experience("c1", "research", "FAILURE", context_key="web"),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="other",
            lineage=("other",),
        ),
        _experience(
            "c3",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c2",
            lineage=("other", "c2"),
        ),
    )

    result = StrategyRecoveryEvaluator().evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.ABSTAIN
    assert result.strategy == "reassess_without_assuming_cause"


def test_bounded_window_remains_enforced() -> None:
    experiences = (
        _experience("old", "research", "FAILURE", context_key="web"),
        _experience(
            "c1",
            "research",
            "FAILURE",
            context_key="web",
            parent_cycle_id="old",
            lineage=("old",),
        ),
        _experience(
            "c2",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c1",
            lineage=("old", "c1"),
        ),
        _experience(
            "c3",
            "recheck_independent_evidence",
            "FAILURE",
            context_key="web",
            parent_cycle_id="c2",
            lineage=("old", "c1", "c2"),
        ),
    )

    result = StrategyRecoveryEvaluator(window=2).evaluate(
        "recheck_independent_evidence",
        experiences,
    )

    assert result.action is StrategyRecoveryAction.ABSTAIN
