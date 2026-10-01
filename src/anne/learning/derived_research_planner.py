from __future__ import annotations

from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.research_planner import (
    ResearchPlan,
    ResearchPlanner,
    ResearchSubquestion,
    SourceDirection,
)


class DerivedResearchPlanner:
    """Create a bounded research plan for proposed derived hypotheses."""

    def __init__(self, *, max_hypotheses: int = 2, max_queries: int = 4) -> None:
        if max_hypotheses < 1 or max_queries < 1:
            raise ValueError("limits must be positive")
        self.max_hypotheses = max_hypotheses
        self.max_queries = max_queries

    def create_plan(self, hypotheses: tuple[DerivedHypothesis, ...]) -> ResearchPlan | None:
        eligible = tuple(
            item for item in hypotheses
            if item.status == "PROPOSED" and item.research_question.strip()
        )[: self.max_hypotheses]
        if not eligible:
            return None
        subquestions = tuple(
            ResearchSubquestion(
                id=f"{item.id}-test",
                question=item.research_question,
                purpose="Independently test a derived inference before later use.",
                source_directions=(SourceDirection.PRIMARY, SourceDirection.INDEPENDENT),
            )
            for item in eligible
        )
        planner = ResearchPlanner(
            max_subquestions=len(subquestions),
            min_independent_sources=2,
            max_queries=self.max_queries,
            max_sources=max(2, self.max_queries),
            stop_on_diminishing_returns=True,
            stop_on_unresolved_contradiction=True,
        )
        return planner.create_plan(
            f"Independently test {len(eligible)} derived hypothesis(es)",
            subquestions=subquestions,
            source_directions=(SourceDirection.PRIMARY, SourceDirection.INDEPENDENT),
        )


__all__ = ["DerivedResearchPlanner"]
