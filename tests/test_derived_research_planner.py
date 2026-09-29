from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_planner import DerivedResearchPlanner


def test_planner_creates_independent_test_plan_for_proposed_hypothesis() -> None:
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim="A and B imply X",
        source_inference_claim="A and B imply X",
        status="PROPOSED",
        research_question="Independently test the joint inference: A and B imply X",
    )
    plan = DerivedResearchPlanner().create_plan((hypothesis,))
    assert plan is not None
    assert len(plan.subquestions) == 1
    assert plan.subquestions[0].id == "DH1-test"
    assert plan.stop_conditions.min_independent_sources == 2
    assert plan.stop_conditions.stop_on_unresolved_contradiction is True


def test_planner_ignores_non_proposed_hypotheses() -> None:
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim="A",
        source_inference_claim="A",
        status="REJECTED",
        research_question="test A",
    )
    assert DerivedResearchPlanner().create_plan((hypothesis,)) is None


def test_planner_is_bounded() -> None:
    hypotheses = tuple(
        DerivedHypothesis(
            id=f"DH{i}",
            claim=f"claim {i}",
            source_inference_claim=f"claim {i}",
            status="PROPOSED",
            research_question=f"test claim {i}",
        )
        for i in range(1, 5)
    )
    plan = DerivedResearchPlanner(max_hypotheses=2, max_queries=4).create_plan(hypotheses)
    assert plan is not None
    assert len(plan.subquestions) == 2
    assert plan.query_budget == 4
