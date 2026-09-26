from __future__ import annotations

import pytest

from anne.learning.research_planner import (
    ResearchPlanner,
    ResearchSubquestion,
    SourceDirection,
)


def test_default_plan_is_bounded_and_inspectable() -> None:
    plan = ResearchPlanner().create_plan("Paris is the capital of France.")
    assert plan.main_question == "Paris is the capital of France."
    assert [item.id for item in plan.subquestions] == ["q1", "q2", "q3"]
    assert plan.query_budget == 6
    assert SourceDirection.INDEPENDENT in plan.source_directions


def test_explicit_subquestions_are_preserved_with_bound() -> None:
    planner = ResearchPlanner(max_subquestions=2)
    supplied = (
        ResearchSubquestion("a", "Question A", "direct"),
        ResearchSubquestion("b", "Question B", "cross-check"),
        ResearchSubquestion("c", "Question C", "extra"),
    )
    plan = planner.create_plan("Main", subquestions=supplied)
    assert tuple(item.id for item in plan.subquestions) == ("a", "b")
    assert plan.as_dict()["stop_conditions"]["max_subquestions"] == 2


def test_stop_on_query_and_source_budget() -> None:
    planner = ResearchPlanner(max_queries=3, max_sources=4)
    assert planner.should_stop(
        independent_sources=0,
        queries_used=3,
        sources_used=1,
    )
    assert planner.should_stop(
        independent_sources=0,
        queries_used=1,
        sources_used=4,
    )


def test_stop_after_independent_corroboration_when_no_contradiction() -> None:
    planner = ResearchPlanner(min_independent_sources=2)
    assert planner.should_stop(
        independent_sources=2,
        queries_used=2,
        sources_used=2,
        contradiction_unresolved=False,
    )


def test_diminishing_returns_stops_when_enabled() -> None:
    planner = ResearchPlanner()
    assert planner.should_stop(
        independent_sources=1,
        queries_used=2,
        sources_used=2,
        diminishing_returns=True,
    )


def test_unresolved_contradiction_is_not_silently_resolved() -> None:
    planner = ResearchPlanner()
    assert not planner.should_stop(
        independent_sources=2,
        queries_used=2,
        sources_used=2,
        contradiction_unresolved=True,
    )

    strict = ResearchPlanner()
    strict.stop_conditions  # immutable contract remains explicit
    assert strict.should_stop(
        independent_sources=1,
        queries_used=2,
        sources_used=2,
        contradiction_unresolved=True,
    ) is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_subquestions": 0},
        {"min_independent_sources": 0},
        {"max_queries": 0},
        {"max_sources": 0},
    ],
)
def test_invalid_limits_fail_closed(**kwargs: int) -> None:
    with pytest.raises(ValueError):
        ResearchPlanner(**kwargs)


def test_empty_question_fails_closed() -> None:
    with pytest.raises(ValueError):
        ResearchPlanner().create_plan("   ")
