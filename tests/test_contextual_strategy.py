from anne.learning.contextual_strategy import (
    ContextualStrategySelector,
    StrategyContext,
)
from anne.learning.experience_learning import Experience


def _experience(
    cycle_id: str,
    strategy: str,
    outcome: str,
    failure_class: str,
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class=failure_class,
        strategy=strategy,
        lesson="observed",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
    )


def test_selector_prefers_observed_success_in_same_failure_context() -> None:
    experiences = (
        _experience("a1", "research", "FAILURE", "evidence_gap"),
        _experience("a2", "recheck_independent_evidence", "SUCCESS", "evidence_gap"),
        _experience("a3", "recheck_independent_evidence", "SUCCESS", "evidence_gap"),
        _experience("a4", "research", "FAILURE", "evidence_gap"),
    )

    result = ContextualStrategySelector().select(
        StrategyContext("evidence_gap"),
        experiences,
        ("research", "recheck_independent_evidence"),
    )

    assert result.strategy == "recheck_independent_evidence"
    assert result.selected_by_observation is True
    assert result.candidates[0].strategy == "recheck_independent_evidence"
    assert result.candidates[0].successes == 2


def test_selector_does_not_transfer_results_across_failure_contexts() -> None:
    experiences = (
        _experience("a1", "research", "FAILURE", "evidence_gap"),
        _experience("a2", "research", "SUCCESS", "semantic"),
    )

    result = ContextualStrategySelector().select(
        StrategyContext("evidence_gap"),
        experiences,
        ("research", "recheck_independent_evidence"),
    )

    assert result.strategy == "research"
    assert result.candidates[0].failures == 1
    assert result.candidates[0].successes == 0


def test_selector_is_deterministic_when_rates_tie() -> None:
    experiences = (
        _experience("a1", "research", "SUCCESS", "factual"),
        _experience("a2", "alternative", "SUCCESS", "factual"),
    )

    result = ContextualStrategySelector().select(
        StrategyContext("factual"),
        experiences,
        ("research", "alternative"),
    )

    assert result.strategy == "research"


def test_selector_does_not_invent_missing_strategy() -> None:
    result = ContextualStrategySelector().select(
        StrategyContext("logical"),
        (),
        ("research",),
    )

    assert result.strategy == "research"
    assert result.selected_by_observation is False
