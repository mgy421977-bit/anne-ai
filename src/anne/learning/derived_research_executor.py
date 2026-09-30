"""Bounded execution of research plans derived from cognitive hypotheses.

The executor gathers evidence only. It never verifies truth, makes decisions,
or grants authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.learning.evidence import EvidenceItem
from anne.learning.research_planner import ResearchPlan
from anne.learning.web_research import WebResearcher


@dataclass(frozen=True)
class DerivedResearchResult:
    """Inspectable result of one bounded derived-research execution."""

    plan_question: str
    evidence: tuple[EvidenceItem, ...]
    queries_used: int
    sources_used: int
    stopped_reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_question": self.plan_question,
            "evidence": [item.__dict__.copy() for item in self.evidence],
            "queries_used": self.queries_used,
            "sources_used": self.sources_used,
            "stopped_reason": self.stopped_reason,
        }


class DerivedResearchExecutor:
    """Execute only the explicit bounded subquestions in a research plan."""

    def __init__(
        self,
        *,
        researcher: WebResearcher | None = None,
        max_evidence_per_question: int = 8,
    ) -> None:
        if max_evidence_per_question < 1:
            raise ValueError("max_evidence_per_question must be >= 1")
        self.researcher = researcher or WebResearcher()
        self.max_evidence_per_question = max_evidence_per_question

    def execute(self, plan: ResearchPlan) -> DerivedResearchResult:
        evidence: list[EvidenceItem] = []
        seen_provenance: set[str] = set()
        queries_used = 0
        stopped_reason = "plan_exhausted"

        for subquestion in plan.subquestions:
            if queries_used >= plan.stop_conditions.max_queries:
                stopped_reason = "query_budget_exhausted"
                break
            if len(seen_provenance) >= plan.stop_conditions.max_sources:
                stopped_reason = "source_budget_exhausted"
                break

            queries_used += 1
            try:
                found = self.researcher.research(subquestion.question)
            except Exception:
                stopped_reason = "retrieval_error"
                continue

            for item in found[: self.max_evidence_per_question]:
                provenance = item.provenance.strip()
                if not provenance or provenance in seen_provenance:
                    continue
                if len(seen_provenance) >= plan.stop_conditions.max_sources:
                    stopped_reason = "source_budget_exhausted"
                    break
                seen_provenance.add(provenance)
                evidence.append(item)

            if len(seen_provenance) >= plan.stop_conditions.max_sources:
                stopped_reason = "source_budget_exhausted"
                break

        return DerivedResearchResult(
            plan_question=plan.main_question,
            evidence=tuple(evidence),
            queries_used=queries_used,
            sources_used=len(seen_provenance),
            stopped_reason=stopped_reason,
        )


__all__ = ["DerivedResearchExecutor", "DerivedResearchResult"]
