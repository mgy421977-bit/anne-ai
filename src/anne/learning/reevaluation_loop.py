"""Bounded feedback loop for provenance-driven re-evaluation.

Re-evaluation invalidates dependent knowledge, gathers fresh evidence, verifies
an explicit stale target, and only creates a replacement when verification
supports that target. Historical nodes are never deleted or rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.verification import (
    BoundedMultiSourceVerifier,
    FactualStatus,
    VerificationResult,
)
from anne.learning.derived_research_executor import (
    DerivedResearchExecutor,
    DerivedResearchResult,
)
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.reevaluation import ReEvaluationPlan, ReEvaluationPlanner
from anne.learning.reevaluation_executor import ReEvaluationExecutor, ReEvaluationResult
from anne.learning.research_planner import ResearchPlan, ResearchPlanner


@dataclass(frozen=True)
class ReEvaluationCycleResult:
    """Inspectable outcome of one bounded re-evaluation cycle."""

    plan: ReEvaluationPlan
    research_plan: ResearchPlan | None
    research_result: DerivedResearchResult | None
    verification: VerificationResult | None
    rebuild: ReEvaluationResult | None

    @property
    def reactivated(self) -> bool:
        return self.rebuild is not None and self.rebuild.action == "REACTIVATED"

    def as_dict(self) -> dict[str, object]:
        return {
            "plan": {
                "invalidated_node": self.plan.invalidated_node,
                "stale_nodes": self.plan.stale_nodes,
                "action": self.plan.action,
                "reason": self.plan.reason,
            },
            "research_plan": (
                None
                if self.research_plan is None
                else {
                    "main_question": self.research_plan.main_question,
                    "subquestions": [
                        item.question for item in self.research_plan.subquestions
                    ],
                }
            ),
            "research_result": (
                None
                if self.research_result is None
                else self.research_result.as_dict()
            ),
            "verification": (
                None
                if self.verification is None
                else self.verification.as_dict()
            ),
            "rebuild": (
                None
                if self.rebuild is None
                else {
                    "stale_node": self.rebuild.stale_node,
                    "replacement_node": self.rebuild.replacement_node,
                    "action": self.rebuild.action,
                    "reason": self.rebuild.reason,
                }
            ),
        }


class ReEvaluationLoop:
    """Run one explicit, bounded invalidation -> research -> verify cycle."""

    def __init__(
        self,
        *,
        planner: ReEvaluationPlanner | None = None,
        research_planner: ResearchPlanner | None = None,
        research_executor: DerivedResearchExecutor | None = None,
        verifier: BoundedMultiSourceVerifier | None = None,
        executor: ReEvaluationExecutor | None = None,
    ) -> None:
        self.planner = planner or ReEvaluationPlanner()
        self.research_planner = research_planner or ResearchPlanner(
            max_subquestions=1,
            min_independent_sources=2,
            max_queries=1,
            max_sources=2,
            stop_on_diminishing_returns=True,
            stop_on_unresolved_contradiction=True,
        )
        self.research_executor = research_executor or DerivedResearchExecutor()
        self.verifier = verifier or BoundedMultiSourceVerifier()
        self.executor = executor or ReEvaluationExecutor()

    def run(
        self,
        ledger: EvidenceLedger,
        *,
        invalidated_evidence_id: str,
        target_node_id: str,
        research_question: str,
    ) -> ReEvaluationCycleResult:
        plan = self.planner.create_plan(ledger.graph, invalidated_evidence_id)
        if not plan.requires_research:
            return ReEvaluationCycleResult(plan, None, None, None, None)

        if target_node_id not in plan.stale_nodes:
            raise ValueError("target_node_id must be a stale downstream node")

        research_plan = self.research_planner.create_plan(research_question)
        research_result = self.research_executor.execute(research_plan)

        fresh_evidence_ids = tuple(
            ledger.record(_to_ledger_entry(item))
            for item in research_result.evidence
        )

        target = ledger.graph.get(target_node_id)
        verification = self.verifier.verify_evidence(
            target.content,
            research_result.evidence,
        )

        if verification.status is not FactualStatus.VERIFIED:
            return ReEvaluationCycleResult(
                plan,
                research_plan,
                research_result,
                verification,
                None,
            )

        if not fresh_evidence_ids:
            return ReEvaluationCycleResult(
                plan,
                research_plan,
                research_result,
                verification,
                None,
            )

        replacement_id = (
            f"{target_node_id}:re{len(ledger.graph.downstream(target_node_id)) + 1}"
        )
        rebuild = self.executor.rebuild(
            ledger.graph,
            stale_node=target_node_id,
            replacement_node=replacement_id,
            replacement_kind=target.kind,
            replacement_content=target.content,
            fresh_evidence_ids=fresh_evidence_ids,
        )
        return ReEvaluationCycleResult(
            plan,
            research_plan,
            research_result,
            verification,
            rebuild,
        )


def _to_ledger_entry(item: EvidenceItem) -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        claim=item.claim,
        source=item.source,
        provenance=item.provenance,
        confidence=item.confidence,
        passage=item.passage,
        support=item.support,
        retrieved_at=item.retrieved_at,
    )


__all__ = ["ReEvaluationCycleResult", "ReEvaluationLoop"]
