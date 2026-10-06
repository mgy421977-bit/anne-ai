from __future__ import annotations

from dataclasses import dataclass

from anne.core.adaptive_resource_planner import AdaptiveResourcePlanner
from anne.core.resource_profile import ResourceProfile


@dataclass
class Observation:
    failure_class: str
    strategy: str
    lesson: str
    outcome: str = "FAILURE"


@dataclass
class MitosOutcome:
    status: str


def test_planner_stays_minimal_without_escalation_signal() -> None:
    decision = AdaptiveResourcePlanner().plan("simple problem")
    assert decision.minimum_sufficient_capacity == 1
    assert decision.profile == ResourceProfile.minimal()


def test_resource_related_experience_escalates_only_as_needed() -> None:
    experiences = [
        Observation(
            "execution",
            "compute_retry",
            "resource budget exhausted",
        ),
        Observation(
            "execution",
            "compute_retry",
            "timeout at iteration budget",
        ),
    ]
    decision = AdaptiveResourcePlanner().plan("problem", experiences=experiences)
    assert decision.minimum_sufficient_capacity == 4
    assert decision.profile.max_mitos_candidates == 8
    assert "historical_experience" in decision.basis


def test_mitos_experience_can_raise_bounded_exploration() -> None:
    outcomes = [
        MitosOutcome("TESTED"),
        MitosOutcome("FAILED"),
        MitosOutcome("INCONCLUSIVE"),
    ]
    decision = AdaptiveResourcePlanner().plan("problem", mitos_outcomes=outcomes)
    assert decision.minimum_sufficient_capacity == 2
    assert decision.profile.max_mitos_candidates == 4


def test_conceptual_failure_does_not_become_resource_failure() -> None:
    decision = AdaptiveResourcePlanner().plan(
        "problem",
        experiences=[
            Observation(
                "semantic",
                "clarify_claim_and_revalidate",
                "hypothesis mismatch",
            )
        ],
    )
    assert decision.minimum_sufficient_capacity == 1


def test_explicit_baseline_is_a_floor() -> None:
    baseline = ResourceProfile.scaled(capacity=2)
    decision = AdaptiveResourcePlanner().plan("problem", baseline=baseline)
    assert decision.minimum_sufficient_capacity == 2
    assert decision.profile == baseline
