from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from anne.learning.critic_loop import CriticLoopController, LoopDecision
from anne.learning.decision_synthesis import DecisionSynthesis, DecisionSynthesizer
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.hypothesis import CriticResult, Hypothesis, HypothesisEngine
from anne.learning.hypothesis_bridge import EvidenceHypothesisBridge
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.reevaluation import ReEvaluationPlan
from anne.learning.research_planner import ResearchPlan, ResearchPlanner


@dataclass(frozen=True)
class ResearchCognitiveState:
    plan: ResearchPlan
    hypotheses: tuple[Hypothesis, ...]
    critic: CriticResult
    synthesis: DecisionSynthesis
    decision: LoopDecision
    evidence_ledger: EvidenceLedger


class ResearchCognitiveLoop:
    """Bounded orchestration of planning, hypotheses, evidence and stopping.

    This component does not perform web access itself. Tool execution remains
    behind the existing research/tool-policy path. The loop only coordinates
    inspectable state and an explicit next-step decision.
    """

    def __init__(
        self,
        *,
        planner: ResearchPlanner | None = None,
        hypothesis_engine: HypothesisEngine | None = None,
        critic_loop: CriticLoopController | None = None,
    ) -> None:
        self.planner = planner or ResearchPlanner()
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.critic_loop = critic_loop or CriticLoopController()
        self.decision_synthesizer = DecisionSynthesizer()

    def initialize(
        self,
        question: str,
        *,
        evidence: Iterable[EvidenceItem] = (),
        queries_used: int = 0,
        sources_used: int = 0,
        max_hypotheses: int = 3,
    ) -> ResearchCognitiveState:
        plan = self.planner.create_plan(question)
        hypotheses = self.hypothesis_engine.generate(
            plan.main_question, max_hypotheses=max_hypotheses
        )
        evidence_items = tuple(evidence)
        critic = EvidenceHypothesisBridge().assess(hypotheses, evidence_items)
        synthesis = self.decision_synthesizer.synthesize(critic)
        evidence_ledger = EvidenceLedger()

        for hypothesis in hypotheses:
            evidence_ledger.graph.add_node(
                ProvenanceNode(hypothesis.id, "hypothesis", hypothesis.claim)
            )

        for item in evidence_items:
            entry = EvidenceLedgerEntry(
                claim=item.claim,
                source=item.source,
                provenance=item.provenance,
                confidence=item.confidence,
                passage=item.passage,
                support=item.support,
            )
            evidence_id = evidence_ledger.record(entry)
            for hypothesis in hypotheses:
                if item.claim.strip() != hypothesis.claim.strip():
                    continue
                relation = item.support.strip().lower() or "unclear"
                evidence_ledger.graph.add_edge(
                    ProvenanceEdge(evidence_id, hypothesis.id, relation)
                )

        synthesis_id = "SYNTHESIS"
        evidence_ledger.graph.add_node(
            ProvenanceNode(
                synthesis_id,
                "decision_synthesis",
                synthesis.reason,
            )
        )
        for hypothesis in hypotheses:
            evidence_ledger.graph.add_edge(
                ProvenanceEdge(hypothesis.id, synthesis_id, "informs")
            )

        decision = self.critic_loop.decide(
            critic,
            queries_used=queries_used,
            max_queries=plan.stop_conditions.max_queries,
            sources_used=sources_used,
            max_sources=plan.stop_conditions.max_sources,
        )
        return ResearchCognitiveState(
            plan,
            hypotheses,
            critic,
            synthesis,
            decision,
            evidence_ledger,
        )

    def continue_from_re_evaluation(
        self,
        plan: ReEvaluationPlan,
        question: str,
        *,
        evidence: Iterable[EvidenceItem] = (),
        queries_used: int = 0,
        sources_used: int = 0,
    ) -> ResearchCognitiveState | None:
        """Resume bounded research only when provenance says re-evaluation is needed."""
        if not plan.requires_research:
            return None
        return self.initialize(
            question,
            evidence=evidence,
            queries_used=queries_used,
            sources_used=sources_used,
        )

    def reassess_with_fresh_evidence(
        self,
        question: str,
        evidence: Iterable[EvidenceItem],
        *,
        queries_used: int = 0,
        sources_used: int = 0,
        max_hypotheses: int = 3,
    ) -> ResearchCognitiveState:
        """Rebuild the bounded cognitive state from fresh evidence.

        Existing hypotheses are not treated as facts; the critic reclassifies
        them from the newly supplied evidence signals.
        """
        return self.initialize(
            question,
            evidence=evidence,
            queries_used=queries_used,
            sources_used=sources_used,
            max_hypotheses=max_hypotheses,
        )

    @staticmethod
    def next_research_questions(
        state: ResearchCognitiveState,
    ) -> tuple[str, ...]:
        """Return bounded research prompts for unresolved hypotheses."""
        if state.decision.action != "RESEARCH":
            return ()
        unresolved = set(state.critic.unresolved_hypotheses)
        if "H1" in unresolved and len(state.plan.subquestions) >= 3:
            return (state.plan.subquestions[2].question,)
        return tuple(
            hypothesis.claim
            for hypothesis in state.hypotheses
            if hypothesis.id in unresolved
        )


__all__ = ["ResearchCognitiveLoop", "ResearchCognitiveState"]
