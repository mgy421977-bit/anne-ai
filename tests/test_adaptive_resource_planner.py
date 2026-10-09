from anne.core.adaptive_resource_planner import AdaptiveResourcePlanner
from anne.core.resource_profile import ResourceProfile


def test_minimal_without_escalation() -> None:
    decision = AdaptiveResourcePlanner().plan("simple question")
    assert decision.minimum_sufficient_capacity == 1
    assert decision.profile.max_mitos_candidates == 2


def test_resource_history_escalates_bounded_capacity() -> None:
    experiences = (
        {"failure_class": "resource_timeout", "safe_to_reuse": False},
        {"failure_class": "compute_budget_exhausted", "safe_to_reuse": False},
    )
    decision = AdaptiveResourcePlanner().plan("hard question", experiences=experiences)
    assert decision.minimum_sufficient_capacity == 4
    assert decision.profile.max_mitos_candidates == 8
    assert decision.experience_profile.resource_failure_count == 2


def test_informative_mitos_outcomes_expand_exploration() -> None:
    outcomes = ({"status": "TESTED"}, {"status": "FAILED"}, {"status": "INCONCLUSIVE"})
    decision = AdaptiveResourcePlanner().plan("research", mitos_outcomes=outcomes)
    assert decision.minimum_sufficient_capacity == 2
    assert decision.profile.max_mitos_candidates == 4


def test_epistemic_structure_can_raise_capacity_without_claiming_truth() -> None:
    outcomes = (
        {"status": "TESTED", "relation_count": 12, "contradiction_count": 2},
    )
    decision = AdaptiveResourcePlanner().plan("hypothesis graph", mitos_outcomes=outcomes)
    assert decision.minimum_sufficient_capacity == 4
    assert "epistemic_complexity" in decision.basis


def test_conceptual_failure_does_not_become_resource_failure() -> None:
    experiences = ({"failure_class": "wrong_hypothesis", "lesson": "new hypothesis needed"},)
    decision = AdaptiveResourcePlanner().plan("hard question", experiences=experiences)
    assert decision.minimum_sufficient_capacity == 1
    assert decision.experience_profile.resource_failure_count == 0


def test_explicit_baseline_is_a_floor() -> None:
    baseline = ResourceProfile.scaled(capacity=2)
    decision = AdaptiveResourcePlanner().plan("question", baseline=baseline)
    assert decision.minimum_sufficient_capacity == 2
    assert decision.profile.cpu_units == 2
