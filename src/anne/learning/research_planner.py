"""Bounded research planning primitives for ANNE.

The planner creates an inspectable research plan without performing web access.
It keeps decomposition, source direction, and stop conditions explicit so a
later execution layer can remain bounded and fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SourceDirection(StrEnum):
    """Coarse source families requested by a research plan."""

    AUTHORITY = "authority"
    PRIMARY = "primary"
    INDEPENDENT = "independent"
    SECONDARY = "secondary"


@dataclass(frozen=True)
class StopConditions:
    """Explicit limits that prevent open-ended research loops."""

    min_independent_sources: int = 2
    max_subquestions: int = 4
    max_queries: int = 8
    max_sources: int = 12
    stop_on_diminishing_returns: bool = True
    stop_on_unresolved_contradiction: bool = False

    def __post_init__(self) -> None:
        if self.min_independent_sources < 1:
            raise ValueError("min_independent_sources must be positive")
        if self.max_subquestions < 1:
            raise ValueError("max_subquestions must be positive")
        if self.max_queries < 1:
            raise ValueError("max_queries must be positive")
        if self.max_sources < self.min_independent_sources:
            raise ValueError("max_sources must cover minimum independent sources")


@dataclass(frozen=True)
class ResearchSubquestion:
    """One bounded question that contributes to the main research question."""

    id: str
    question: str
    purpose: str
    source_directions: tuple[SourceDirection, ...] = (
        SourceDirection.PRIMARY,
        SourceDirection.INDEPENDENT,
    )

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.question.strip() or not self.purpose.strip():
            raise ValueError("subquestion id, question and purpose are required")
        if not self.source_directions:
            raise ValueError("subquestion needs at least one source direction")


@dataclass(frozen=True)
class ResearchPlan:
    """Inspectable, bounded research plan; it does not execute tools."""

    main_question: str
    subquestions: tuple[ResearchSubquestion, ...]
    source_directions: tuple[SourceDirection, ...]
    stop_conditions: StopConditions = field(default_factory=StopConditions)

    def __post_init__(self) -> None:
        if not self.main_question.strip():
            raise ValueError("main_question must not be empty")
        if not self.subquestions:
            raise ValueError("research plan needs at least one subquestion")
        if len(self.subquestions) > self.stop_conditions.max_subquestions:
            raise ValueError("subquestions exceed plan limit")
        if not self.source_directions:
            raise ValueError("research plan needs source directions")

    @property
    def query_budget(self) -> int:
        return min(self.stop_conditions.max_queries, len(self.subquestions) * 2)

    def as_dict(self) -> dict[str, object]:
        return {
            "main_question": self.main_question,
            "subquestions": [
                {
                    "id": item.id,
                    "question": item.question,
                    "purpose": item.purpose,
                    "source_directions": [
                        direction.value for direction in item.source_directions
                    ],
                }
                for item in self.subquestions
            ],
            "source_directions": [direction.value for direction in self.source_directions],
            "stop_conditions": {
                "min_independent_sources": self.stop_conditions.min_independent_sources,
                "max_subquestions": self.stop_conditions.max_subquestions,
                "max_queries": self.stop_conditions.max_queries,
                "max_sources": self.stop_conditions.max_sources,
                "stop_on_diminishing_returns": (
                    self.stop_conditions.stop_on_diminishing_returns
                ),
                "stop_on_unresolved_contradiction": (
                    self.stop_conditions.stop_on_unresolved_contradiction
                ),
            },
            "query_budget": self.query_budget,
        }


class ResearchPlanner:
    """Deterministic planner for a single research question.

    If the caller supplies explicit subquestions they are preserved. Otherwise
    the planner creates a minimal three-part plan: answer the main question,
    seek independent corroboration, and test for contradiction or uncertainty.
    No semantic claim of completeness is made.
    """

    def __init__(
        self,
        *,
        max_subquestions: int = 4,
        min_independent_sources: int = 2,
        max_queries: int = 8,
        max_sources: int = 12,
        stop_on_diminishing_returns: bool = True,
        stop_on_unresolved_contradiction: bool = False,
    ) -> None:
        self.stop_conditions = StopConditions(
            min_independent_sources=min_independent_sources,
            max_subquestions=max_subquestions,
            max_queries=max_queries,
            max_sources=max_sources,
            stop_on_diminishing_returns=stop_on_diminishing_returns,
            stop_on_unresolved_contradiction=stop_on_unresolved_contradiction,
        )

    def create_plan(
        self,
        main_question: str,
        *,
        subquestions: tuple[ResearchSubquestion, ...] | None = None,
        source_directions: tuple[SourceDirection, ...] = (
            SourceDirection.PRIMARY,
            SourceDirection.INDEPENDENT,
        ),
    ) -> ResearchPlan:
        if not main_question.strip():
            raise ValueError("main_question must not be empty")
        if not source_directions:
            raise ValueError("source_directions must not be empty")

        if subquestions is None:
            subquestions = self._default_subquestions(main_question, source_directions)

        bounded = tuple(subquestions[: self.stop_conditions.max_subquestions])
        if not bounded:
            raise ValueError("at least one subquestion is required")
        return ResearchPlan(
            main_question=main_question.strip(),
            subquestions=bounded,
            source_directions=tuple(source_directions),
            stop_conditions=self.stop_conditions,
        )

    @staticmethod
    def _default_subquestions(
        main_question: str,
        source_directions: tuple[SourceDirection, ...],
    ) -> tuple[ResearchSubquestion, ...]:
        return (
            ResearchSubquestion(
                id="q1",
                question=main_question.strip(),
                purpose="Establish the direct answer or primary factual basis.",
                source_directions=source_directions,
            ),
            ResearchSubquestion(
                id="q2",
                question=f"Find independent evidence relevant to: {main_question.strip()}",
                purpose="Cross-check the main question using an independent publisher family.",
                source_directions=(
                    SourceDirection.INDEPENDENT,
                    SourceDirection.SECONDARY,
                ),
            ),
            ResearchSubquestion(
                id="q3",
                question=(
                    "Look for credible evidence that contradicts or qualifies: "
                    f"{main_question.strip()}"
                ),
                purpose="Expose contradictions, limitations, or unresolved uncertainty.",
                source_directions=(
                    SourceDirection.PRIMARY,
                    SourceDirection.INDEPENDENT,
                ),
            ),
        )

    def should_stop(
        self,
        *,
        independent_sources: int,
        queries_used: int,
        sources_used: int,
        contradiction_unresolved: bool = False,
        diminishing_returns: bool = False,
    ) -> bool:
        limits = self.stop_conditions
        if queries_used >= limits.max_queries or sources_used >= limits.max_sources:
            return True
        if (
            independent_sources >= limits.min_independent_sources
            and (diminishing_returns or not contradiction_unresolved)
        ):
            return True
        if contradiction_unresolved and limits.stop_on_unresolved_contradiction:
            return True
        return diminishing_returns and limits.stop_on_diminishing_returns


__all__ = [
    "ResearchPlan",
    "ResearchPlanner",
    "ResearchSubquestion",
    "SourceDirection",
    "StopConditions",
]
