"""Bounded web re-evaluation after explicit provenance invalidation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from anne.learning.evidence import (
    EvidenceItem,
    EvidenceLedger,
    EvidenceLedgerEntry,
)
from anne.learning.reevaluation import ReEvaluationPlan
from anne.learning.research_cognitive_loop import ResearchCognitiveState, ResearchCognitiveLoop


class ResearchProvider(Protocol):
    """Minimal retrieval contract used by the bounded re-evaluation bridge."""

    def research(self, query: str) -> Sequence[EvidenceItem]:
        ...


@dataclass(frozen=True)
class WebReEvaluationResult:
    """Inspectable result of one explicitly triggered fresh research pass."""

    plan: ReEvaluationPlan
    fresh_evidence: tuple[EvidenceItem, ...]
    fresh_evidence_ids: tuple[str, ...]
    queries_used: int
    sources_used: int
    refreshed_state: ResearchCognitiveState | None = None


class BoundedWebReEvaluator:
    """Bridge explicit invalidation to one bounded fresh web-research pass.

    Retrieval never decides that evidence is invalid. The caller must identify
    the evidence node to invalidate; the provenance planner decides whether
    downstream research is required. This class performs at most one retrieval
    pass per invocation and records only genuinely new evidence in the ledger.
    """

    def __init__(self, researcher: ResearchProvider, *, max_sources: int = 12) -> None:
        if max_sources < 1:
            raise ValueError("max_sources must be positive")
        self.researcher = researcher
        self.max_sources = max_sources

    def reevaluate(
        self,
        *,
        question: str,
        ledger: EvidenceLedger,
        evidence_id: str,
    ) -> WebReEvaluationResult:
        """Invalidate one explicit dependency and, if required, research once."""
        if not question.strip():
            raise ValueError("question must not be empty")

        plan = ledger.re_evaluation_plan(evidence_id)
        if not plan.requires_research:
            return WebReEvaluationResult(
                plan=plan,
                fresh_evidence=(),
                fresh_evidence_ids=(),
                queries_used=0,
                sources_used=0,
                refreshed_state=None,
            )

        # The bridge deliberately performs a single bounded retrieval pass.
        # A future multi-pass design must remain explicitly budgeted and
        # separately testable rather than becoming an implicit autonomous loop.

        retrieved = tuple(self.researcher.research(question))[: self.max_sources]
        fresh_items: list[EvidenceItem] = []
        fresh_ids: list[str] = []

        for item in retrieved:
            entry = EvidenceLedgerEntry(
                claim=item.claim,
                source=item.source,
                provenance=item.provenance,
                confidence=item.confidence,
                passage=item.passage,
                support=item.support,
            )
            item_id = ledger.evidence_id(entry)
            if item_id in fresh_ids:
                continue
            try:
                ledger.get(item_id)
            except KeyError:
                ledger.record(entry)
                fresh_items.append(item)
                fresh_ids.append(item_id)

        refreshed_state = None
        if fresh_items:
            refreshed_state = ResearchCognitiveLoop().continue_from_re_evaluation(
                plan,
                question,
                evidence=fresh_items,
                queries_used=1,
                sources_used=len(fresh_items),
            )

        return WebReEvaluationResult(
            plan=plan,
            fresh_evidence=tuple(fresh_items),
            fresh_evidence_ids=tuple(fresh_ids),
            queries_used=1,
            sources_used=len(fresh_items),
            refreshed_state=refreshed_state,
        )


__all__ = [
    "BoundedWebReEvaluator",
    "ResearchProvider",
    "WebReEvaluationResult",
]
