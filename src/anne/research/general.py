"""General-purpose, bounded research engine for ANNE.

The engine is domain-neutral. Clients such as VITA Intelligence and Tinker
submit a research mission; the engine retrieves candidate sources and keeps
their verification state explicit. Domain-specific interpretation belongs in
adapters, not in the research core.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence
from uuid import uuid4

from anne.research.web_search import (
    WebResearchMission,
    WebResearchRunner,
    WebSearchProvider,
    WebSearchResult,
)


@dataclass(frozen=True)
class ResearchMission:
    """A client-neutral research request."""

    objective: str
    scope: str = ""
    questions: tuple[str, ...] = ()
    max_searches: int = 5
    max_results_per_search: int = 10
    recency_days: int | None = None
    domains: tuple[str, ...] = ()
    mission_id: str = field(default_factory=lambda: f"research_{uuid4().hex[:12]}")

    def validate(self) -> None:
        if not self.objective.strip():
            raise ValueError("objective is required")
        if self.max_searches < 1:
            raise ValueError("max_searches must be positive")
        if self.max_results_per_search < 1:
            raise ValueError("max_results_per_search must be positive")
        if self.recency_days is not None and self.recency_days < 0:
            raise ValueError("recency_days cannot be negative")
        if any(not question.strip() for question in self.questions):
            raise ValueError("questions cannot contain empty values")


@dataclass(frozen=True)
class ResearchReport:
    """Research output before domain-specific verification."""

    mission_id: str
    objective: str
    scope: str
    queries: tuple[str, ...]
    sources: tuple[WebSearchResult, ...]
    evidence_status: str
    verification_status: str
    notes: tuple[str, ...] = ()


class GeneralResearchEngine:
    """Run bounded research without turning retrieval into fact."""

    def __init__(self, search_provider: WebSearchProvider) -> None:
        self._web = WebResearchRunner(search_provider)

    @staticmethod
    def build_queries(mission: ResearchMission) -> tuple[str, ...]:
        candidates = [mission.objective, *mission.questions]
        return tuple(dict.fromkeys(q.strip() for q in candidates if q.strip()))[: mission.max_searches]

    def research(self, mission: ResearchMission) -> ResearchReport:
        mission.validate()
        queries = self.build_queries(mission)
        if not queries:
            raise ValueError("research mission requires an objective or question")

        web_mission = WebResearchMission(
            objective=mission.objective,
            scope=mission.scope or "general",
            max_searches=mission.max_searches,
            max_results_per_search=mission.max_results_per_search,
            mission_id=mission.mission_id,
        )
        result = self._web.run(
            web_mission,
            queries,
            recency_days=mission.recency_days,
            domains=mission.domains,
        )
        return ResearchReport(
            mission_id=mission.mission_id,
            objective=mission.objective,
            scope=mission.scope,
            queries=tuple(queries),
            sources=result.results,
            evidence_status=result.evidence_status,
            verification_status=result.verification_status,
            notes=(
                *result.notes,
                "Research output is candidate evidence until ANNE verification completes.",
            ),
        )


__all__ = ["ResearchMission", "ResearchReport", "GeneralResearchEngine"]
