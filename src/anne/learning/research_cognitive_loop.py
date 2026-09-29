from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator, AdaptiveLearningResult
from anne.learning.critic_loop import CriticLoopController, LoopDecision
from anne.learning.decision_synthesis import DecisionSynthesis, DecisionSynthesizer
from anne.learning.derived_hypothesis import DerivedHypothesis, DerivedHypothesisGenerator
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.experience_learning import Experience
from anne.learning.hypothesis import CriticResult, Hypothesis, HypothesisEngine
from anne.learning.hypothesis_bridge import EvidenceHypothesisBridge
from anne.learning.joint_inference import JointInference, JointInferenceEngine
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
    joint_inferences: tuple[JointInference, ...] = ()
    derived_hypotheses: tuple[DerivedHypothesis, ...] = ()
    adaptive_learning: AdaptiveLearningResult | None = None


class ResearchCognitiveLoop:
    """Bounded orchestration of research plus observed-cycle learning.

    Research remains evidence gathering, never authority. Adaptive learning
    observes completed traces and can recommend the next bounded step, but it
    does not execute tools, grant authority, or weaken safety gates.
    """

    def __init__(
        self,
        *,
        planner: ResearchPlanner | None = None,
        hypothesis_engine: HypothesisEngine | None = None,
        critic_loop: CriticLoopController | None = None,
        adaptive_learning: AdaptiveLearningCoordinator | None = None,
    ) -> None:
        self.planner = planner or ResearchPlanner()
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.critic_loop = critic_loop or CriticLoopController()
        self.decision_synthesizer = DecisionSynthesizer()
        self.adaptive_learning = adaptive_learning or AdaptiveLearningCoordinator()

    def initialize(
        self,
        question: str,
        *,
        evidence: Iterable[EvidenceItem] = (),
        queries_used: int = 0,
        sources_used: int = 0,
        max_hypotheses: int = 3,
        completed_trace: CycleTrace | None = None,
        strategy: str = "research",
        prior_experiences: tuple[Experience, ...] = (),
    ) -> ResearchCognitiveState:
        plan = self.planner.create_plan(question)
        hypotheses = self.hypothesis_engine.generate(
            plan.main_question, max_hypotheses=max_hypotheses
        )
        evidence_items = tuple(evidence)
        critic = EvidenceHypothesisBridge().assess(hypotheses, evidence_items)
        synthesis = self.decision_synthesizer.synthesize(critic)
        evidence_ledger = EvidenceLedger()
        joint_inference_engine = JointInferenceEngine()
        derived_hypothesis_generator = DerivedHypothesisGenerator()

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

        joint_inferences: list[JointInference] = []
        for hypothesis in hypotheses:
            premise_ids: list[str] = []
            for item in evidence_items:
                if item.claim.strip() != hypothesis.claim.strip():
                    continue
                entry = EvidenceLedgerEntry(
                    claim=item.claim,
                    source=item.source,
                    provenance=item.provenance,
                    confidence=item.confidence,
                    passage=item.passage,
                    support=item.support,
                    retrieved_at=item.retrieved_at,
                )
                premise_ids.append(evidence_ledger.evidence_id(entry))
            if premise_ids:
                joint_inferences.append(
                    joint_inference_engine.infer(
                        claim=hypothesis.claim,
                        evidence_ids=tuple(premise_ids),
                        ledger=evidence_ledger,
                    )
                )

        derived_hypotheses = derived_hypothesis_generator.generate(tuple(joint_inferences))

        synthesis_id = "SYNTHESIS"
        evidence_ledger.graph.add_node(
            ProvenanceNode(synthesis_id, "decision_synthesis", synthesis.reason)
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

        adaptive_result = None
        if completed_trace is not None:
            adaptive_result = self.adaptive_learning.observe(
                completed_trace,
                strategy=strategy,
                prior_experiences=prior_experiences,
            )
            if (
                adaptive_result.strategy.action == "CHANGE"
                and adaptive_result.strategy.strategy
                == "seek_fresh_independent_evidence"
                and decision.research_allowed
            ):
                decision = LoopDecision(
                    action="RESEARCH",
                    reason=adaptive_result.strategy.reason,
                    research_allowed=True,
                )

        return ResearchCognitiveState(
            plan,
            hypotheses,
            critic,
            synthesis,
            decision,
            evidence_ledger,
            tuple(joint_inferences),
            derived_hypotheses,
            adaptive_result,
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
        return self.initialize(
            question,
            evidence=evidence,
            queries_used=queries_used,
            sources_used=sources_used,
            max_hypotheses=max_hypotheses,
        )

    @staticmethod
    def next_research_questions(state: ResearchCognitiveState) -> tuple[str, ...]:
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
