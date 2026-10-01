"""Bounded web re-evaluation after explicit provenance invalidation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from anne.core.verification import BoundedMultiSourceVerifier, VerificationResult
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.reevaluation import ReEvaluationPlan
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop, ResearchCognitiveState


class ResearchProvider(Protocol):
    """Minimal retrieval contract used by the bounded re-evaluation bridge."""

    def research(self, query: str) -> Sequence[EvidenceItem]: ...


@dataclass(frozen=True)
class WebReEvaluationResult:
    """Inspectable result of one explicitly triggered fresh research pass."""

    plan: ReEvaluationPlan
    fresh_evidence: tuple[EvidenceItem, ...]
    fresh_evidence_ids: tuple[str, ...]
    queries_used: int
    sources_used: int
    verification: VerificationResult
    refreshed_state: ResearchCognitiveState | None = None


class BoundedWebReEvaluator:
    """Bridge explicit invalidation to one bounded fresh web-research pass.

    Retrieval never decides that evidence is invalid. The caller must identify
    the evidence node to invalidate; provenance decides whether research is
    required. Fresh evidence must independently verify before state refresh.
    """

    def __init__(
        self,
        researcher: ResearchProvider,
        *,
        verifier: BoundedMultiSourceVerifier | None = None,
        max_sources: int = 12,
    ) -> None:
        if max_sources < 1:
            raise ValueError("max_sources must be positive")
        self.researcher = researcher
        self.verifier = verifier or BoundedMultiSourceVerifier()
        self.max_sources = max_sources

    def reevaluate(
        self,
        *,
        question: str,
        ledger: EvidenceLedger,
        evidence_id: str,
    ) -> WebReEvaluationResult:
        if not question.strip():
            raise ValueError("question must not be empty")

        plan = ledger.re_evaluation_plan(evidence_id)
        if not plan.requires_research:
            return WebReEvaluationResult(
                plan, (), (), 0, 0, VerificationResult(), None
            )

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

        verification = self.verifier.verify_evidence(question, tuple(fresh_items))
        refreshed_state = None
        if fresh_items and verification.status.value == "verified":
            refreshed_state = ResearchCognitiveLoop().continue_from_re_evaluation(
                plan,
                question,
                evidence=fresh_items,
                queries_used=1,
                sources_used=len(fresh_items),
            )

        return WebReEvaluationResult(
            plan,
            tuple(fresh_items),
            tuple(fresh_ids),
            1,
            len(fresh_items),
            verification,
            refreshed_state,
        )


__all__ = ["BoundedWebReEvaluator", "ResearchProvider", "WebReEvaluationResult"]
