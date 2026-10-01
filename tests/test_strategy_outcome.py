from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyDecision
from anne.learning.strategy_outcome import (
    StrategyEffectiveness,
    StrategyOutcomeEvaluator,
)


def _experience(
    cycle_id: str,
    *,
    strategy: str,
    outcome: str,
    failure_class: str = "unknown",
    lineage: tuple[str, ...] = (),
    parent_cycle_id: str | None = None,
) -> Experience:
    return Experience(
        source_cycle_id=cycle_id,
        outcome=outcome,
        failure_class=failure_class,
        strategy=strategy,
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        parent_cycle_id=parent_cycle_id,
        lineage=lineage,
    )


def test_changed_strategy_followed_by_success_is_observed_as_improvement() -> None:
    experiences = (
        _experience(
            "c1",
            strategy="research",
            outcome="FAILURE",
            failure_class="evidence_gap",
            lineage=("c1",),
        ),
        _experience(
            "c2",
            strategy="recheck_independent_evidence",
            outcome="SUCCESS",
            lineage=("c1", "c2"),
        ),
    )
    decision = StrategyDecision(
        "KEEP",
        "recheck_independent_evidence",
        "observe",
    )

    result = StrategyOutcomeEvaluator().evaluate(decision, experiences)

    assert result.effectiveness is StrategyEffectiveness.IMPROVED
    assert result.compared_cycle_ids == ("c1", "c2")
    assert result.causal_claim is False


def test_changed_strategy_followed_by_failure_is_not_improved() -> None:
    experiences = (
        _experience(
            "c1",
            strategy="research",
            outcome="FAILURE",
            failure_class="evidence_gap",
            lineage=("c1",),
        ),
        _experience(
            "c2",
            strategy="recheck_independent_evidence",
            outcome="FAILURE",
            failure_class="evidence_gap",
            lineage=("c1", "c2"),
        ),
    )
    decision = StrategyDecision(
        "KEEP",
        "recheck_independent_evidence",
        "observe",
    )

    result = StrategyOutcomeEvaluator().evaluate(decision, experiences)

    assert result.effectiveness is StrategyEffectiveness.NOT_IMPROVED


def test_same_strategy_is_not_mistaken_for_learning() -> None:
    experiences = (
        _experience("c1", strategy="research", outcome="FAILURE", lineage=("c1",)),
        _experience("c2", strategy="research", outcome="SUCCESS", lineage=("c1", "c2")),
    )
    decision = StrategyDecision("KEEP", "research", "observe")

    result = StrategyOutcomeEvaluator().evaluate(decision, experiences)

    assert result.effectiveness is StrategyEffectiveness.NO_CHANGE


def test_first_observation_is_insufficient() -> None:
    decision = StrategyDecision("KEEP", "research", "observe")
    result = StrategyOutcomeEvaluator().evaluate(
        decision,
        (_experience("c1", strategy="research", outcome="SUCCESS"),),
    )

    assert result.effectiveness is StrategyEffectiveness.INSUFFICIENT_OBSERVATION


def test_adaptive_trace_records_strategy_outcome_without_authority() -> None:
    prior = _experience(
        "c1",
        strategy="research",
        outcome="FAILURE",
        failure_class="evidence_gap",
    )
    trace = CycleTrace(
        cycle_id="c2",
        status="SUCCESS",
        verification={"status": "VERIFIED"},
        lineage=("c1", "c2"),
    )

    result = AdaptiveLearningCoordinator().observe(
        trace,
        strategy="recheck_independent_evidence",
        prior_experiences=(prior,),
    )

    assert result.strategy_outcome.effectiveness is StrategyEffectiveness.IMPROVED
    assert result.strategy_outcome.causal_claim is False
    assert result.trace.learning["strategy_outcome"]["effectiveness"] == "improved"
    assert result.trace.learning["strategy_outcome"]["causal_claim"] is False


def test_strategy_outcome_does_not_compare_different_explicit_contexts() -> None:
    previous = Experience(
        source_cycle_id="c-context-1",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "1"),),
    )
    latest = Experience(
        source_cycle_id="c-context-2",
        outcome="SUCCESS",
        failure_class="evidence_gap",
        strategy="recheck_independent_evidence",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "2"),),
    )
    decision = StrategyDecision(
        "CHANGE",
        "recheck_independent_evidence",
        "selected_from_observed_exact_context_outcomes",
    )

    result = StrategyOutcomeEvaluator().evaluate(decision, (previous, latest))

    assert result.effectiveness is StrategyEffectiveness.INSUFFICIENT_OBSERVATION
    assert "different_explicit_context" in result.reason


def test_strategy_outcome_requires_explicit_cycle_lineage() -> None:
    previous = Experience(
        source_cycle_id="c-lineage-1",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "2"),),
        lineage=("c-lineage-1",),
    )
    latest = Experience(
        source_cycle_id="c-lineage-2",
        outcome="SUCCESS",
        failure_class="evidence_gap",
        strategy="recheck_independent_evidence",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "2"),),
        lineage=("c-lineage-2",),
    )
    decision = StrategyDecision(
        "CHANGE",
        "recheck_independent_evidence",
        "selected_from_observed_exact_context_outcomes",
    )

    result = StrategyOutcomeEvaluator().evaluate(decision, (previous, latest))

    assert result.effectiveness is StrategyEffectiveness.INSUFFICIENT_OBSERVATION
    assert "same_explicit_cycle_lineage" in result.reason


def test_strategy_outcome_accepts_parent_cycle_lineage() -> None:
    previous = Experience(
        source_cycle_id="c-parent",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "2"),),
        lineage=("c-parent",),
    )
    latest = Experience(
        source_cycle_id="c-child",
        outcome="SUCCESS",
        failure_class="evidence_gap",
        strategy="recheck_independent_evidence",
        lesson="observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("source_count", "2"),),
        parent_cycle_id="c-parent",
        lineage=("c-parent", "c-child"),
    )
    decision = StrategyDecision(
        "CHANGE",
        "recheck_independent_evidence",
        "selected_from_observed_exact_context_outcomes",
    )

    result = StrategyOutcomeEvaluator().evaluate(decision, (previous, latest))

    assert result.effectiveness is StrategyEffectiveness.IMPROVED
