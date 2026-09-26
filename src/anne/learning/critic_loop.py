from __future__ import annotations

from dataclasses import dataclass

from anne.learning.hypothesis import CriticResult


@dataclass(frozen=True)
class LoopDecision:
    action: str
    reason: str
    research_allowed: bool


class CriticLoopController:
    """Bounded controller for the hypothesis/research loop."""

    def decide(
        self,
        critic_result: CriticResult,
        *,
        queries_used: int,
        max_queries: int,
        sources_used: int = 0,
        max_sources: int = 12,
    ) -> LoopDecision:
        if queries_used < 0 or max_queries < 1:
            raise ValueError("invalid query budget")
        if sources_used < 0 or max_sources < 1:
            raise ValueError("invalid source budget")

        if not critic_result.needs_more_research:
            return LoopDecision(
                action="PROCEED",
                reason="No unresolved hypothesis requires additional research.",
                research_allowed=False,
            )

        if queries_used >= max_queries:
            return LoopDecision(
                action="STOP",
                reason="Query budget exhausted while uncertainty remains.",
                research_allowed=False,
            )

        if sources_used >= max_sources:
            return LoopDecision(
                action="STOP",
                reason="Source budget exhausted while uncertainty remains.",
                research_allowed=False,
            )

        return LoopDecision(
            action="RESEARCH",
            reason="Unresolved hypothesis remains and research budget is available.",
            research_allowed=True,
        )
