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
    context_key: str = "",
    conditions: tuple[tuple[str, str], ...] = (),
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class=failure_class,
        strategy=strategy,
        lesson="observed",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context_key,
        context_conditions=conditions,
    )


def test_selector_prefers_observed_success_in_same_failure_context() -> None:
    experiences = (
        _experience("a1", "research", "FAILURE", "evidence_gap"),
        _experience(
            "a2",
            "recheck_independent_evidence",
            "SUCCESS",
            "evidence_gap",
        ),
        _experience(
            "a3",
            "recheck_independent_evidence",
            "SUCCESS",
            "evidence_gap",
        ),
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


def test_selector_requires_exact_context_key_and_conditions() -> None:
    experiences = (
        _experience(
            "a1",
            "research",
            "FAILURE",
            "evidence_gap",
            "web_research",
            (("source_count", "1"), ("freshness", "stale")),
        ),
        _experience(
            "a2",
            "recheck_independent_evidence",
            "SUCCESS",
            "evidence_gap",
            "web_research",
            (("source_count", "2"), ("freshness", "current")),
        ),
    )

    result = ContextualStrategySelector().select(
        StrategyContext(
            "evidence_gap",
            "web_research",
            (("freshness", "current"), ("source_count", "2")),
        ),
        experiences,
        ("research", "recheck_independent_evidence"),
    )

    assert result.strategy == "recheck_independent_evidence"
    assert result.candidates[0].successes == 1
    assert result.candidates[0].observations == 1


def test_selector_does_not_transfer_same_failure_class_across_conditions() -> None:
    experiences = (
        _experience(
            "a1",
            "research",
            "SUCCESS",
            "evidence_gap",
            "web_research",
            (("source_count", "1"),),
        ),
    )

    result = ContextualStrategySelector().select(
        StrategyContext(
            "evidence_gap",
            "web_research",
            (("source_count", "2"),),
        ),
        experiences,
        ("research",),
    )

    assert result.selected_by_observation is False
    assert result.reason == "no_observed_candidate_for_exact_context"


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


def test_selector_bounds_candidates_and_history() -> None:
    experiences = tuple(
        _experience(
            f"cycle-{index}",
            "research",
            "SUCCESS",
            "evidence_gap",
        )
        for index in range(4)
    )

    result = ContextualStrategySelector(
        max_experiences=2,
        max_candidates=1,
    ).select(
        StrategyContext("evidence_gap"),
        experiences,
        ("research", "alternative"),
    )

    assert result.candidates[0].observations == 2
    assert result.candidates[0].source_cycle_ids == ("cycle-2", "cycle-3")
