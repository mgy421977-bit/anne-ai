from __future__ import annotations

from anne.agent.runtime import AnneAgent
from anne.learning.research_planner import ResearchPlanner


def test_agent_creates_bounded_research_plan() -> None:
    agent = object.__new__(AnneAgent)
    agent.research_planner = ResearchPlanner(max_subquestions=3, max_queries=6)
    plan = agent._create_research_plan("What is the capital of France?")
    assert plan.main_question == "What is the capital of France?"
    assert len(plan.subquestions) == 3
    assert plan.query_budget == 6
    assert plan.stop_conditions.max_queries == 6
