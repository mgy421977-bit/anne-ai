from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from anne.core.trace import CycleTrace
from anne.core.verification import BoundedMultiSourceVerifier, VerificationResult
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator, AdaptiveLearningResult
from anne.learning.metacognitive_controller import MetacognitiveController
from anne.learning.critic_loop import CriticLoopController, LoopDecision
from anne.learning.decision_synthesis import DecisionSynthesis, DecisionSynthesizer
from anne.learning.derived_hypothesis import DerivedHypothesis, DerivedHypothesisGenerator
from anne.learning.derived_research_executor import DerivedResearchExecutor, DerivedResearchResult
from anne.learning.derived_research_planner import DerivedResearchPlanner
from anne.core.intent import IntentClassifier
from anne.language.corroboration import LanguageCorroborationResult, TurkishLanguageCorroborationService
from anne.language.service import LanguageCheckResult, TurkishLanguageEvidenceService
from anne.language.learning import to_evidence_items
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.experience_learning import Experience
from anne.learning.hypothesis import CriticResult, Hypothesis, HypothesisEngine
from anne.learning.hypothesis_bridge import EvidenceHypothesisBridge
from anne.learning.joint_inference import JointInference, JointInferenceEngine
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.reevaluation import ReEvaluationPlan
from anne.learning.reevaluation_learning import ReEvaluationLearningAdapter
from anne.learning.reevaluation_loop import ReEvaluationCycleResult, ReEvaluationLoop
from anne.learning.research_planner import ResearchPlan, ResearchPlanner
from anne.memory.fractal_memory import FractalMemory


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
    derived_research_plan: ResearchPlan | None = None
    derived_research_result: DerivedResearchResult | None = None
    derived_verifications: tuple[VerificationResult, ...] = ()
    re_evaluation: ReEvaluationCycleResult | None = None
    adaptive_learning: AdaptiveLearningResult | None = None
    language_check: LanguageCheckResult | None = None
    language_corroboration: LanguageCorroborationResult | None = None


class ResearchCognitiveLoop:
    """Bounded orchestration of research plus observed-cycle learning."""

    def __init__(
        self,
        *,
        planner: ResearchPlanner | None = None,
        hypothesis_engine: HypothesisEngine | None = None,
        critic_loop: CriticLoopController | None = None,
        adaptive_learning: AdaptiveLearningCoordinator | None = None,
        derived_research_planner: DerivedResearchPlanner | None = None,
        memory: FractalMemory | None = None,
        language_service: TurkishLanguageEvidenceService | None = None,
        language_corroboration_service: TurkishLanguageCorroborationService | None = None,
    ) -> None:
        self.planner = planner or ResearchPlanner()
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.critic_loop = critic_loop or CriticLoopController()
        self.decision_synthesizer = DecisionSynthesizer()
        self.adaptive_learning = adaptive_learning or AdaptiveLearningCoordinator()
        self.metacognitive_controller = MetacognitiveController()
        self.derived_research_planner = derived_research_planner or DerivedResearchPlanner()
        self.memory = memory
        self.language_service = language_service
        self.language_corroboration_service = language_corroboration_service

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
        language_check = None
        language_corroboration = None
        language_evidence: tuple[EvidenceItem, ...] = ()
        intent = None
        if self.language_service is not None or self.language_corroboration_service is not None:
            intent = IntentClassifier().classify(question)
        if self.language_service is not None and intent is not None:
            language_check = self.language_service.check(question, intent)
            language_evidence = language_check.evidence
        if self.language_corroboration_service is not None and intent is not None:
            language_corroboration = self.language_corroboration_service.check(question, intent)
            corroboration_evidence = tuple(
                item
                for lookup in language_corroboration.lookups
                for item in to_evidence_items(lookup)
            )
            language_evidence = (*language_evidence, *corroboration_evidence)

        plan = self.planner.create_plan(question)
        hypotheses = self.hypothesis_engine.generate(
            plan.main_question, max_hypotheses=max_hypotheses
        )
        evidence_items = (*language_evidence, *tuple(evidence))
        critic = EvidenceHypothesisBridge().assess(hypotheses, evidence_items)
        synthesis = self.decision_synthesizer.synthesize(critic)
        evidence_ledger = EvidenceLedger()
        joint_inference_engine = JointInferenceEngine()

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
                retrieved_at=item.retrieved_at,
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
            premise_ids = tuple(
                evidence_ledger.evidence_id(
                    EvidenceLedgerEntry(
                        claim=item.claim,
                        source=item.source,
                        provenance=item.provenance,
                        confidence=item.confidence,
                        passage=item.passage,
                        support=item.support,
                        retrieved_at=item.retrieved_at,
                    )
                )
                for item in evidence_items
                if item.claim.strip() == hypothesis.claim.strip()
            )
            if premise_ids:
                joint_inferences.append(
                    joint_inference_engine.infer(
                        claim=hypothesis.claim,
                        evidence_ids=premise_ids,
                        ledger=evidence_ledger,
                    )
                )

        derived_hypotheses = DerivedHypothesisGenerator().generate(tuple(joint_inferences))
        derived_research_plan = self.derived_research_planner.create_plan(derived_hypotheses)

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
            observation_trace = completed_trace
            if language_corroboration is not None:
                verification = language_corroboration.verification
                if verification is not None:
                    observation_trace = replace(
                        completed_trace,
                        language_corroboration={
                            "status": verification.status.value,
                            "authoritative": verification.authoritative,
                            "providers": [
                                lookup.provider
                                for lookup in language_corroboration.lookups
                            ],
                        },
                    )
            adaptive_result = self.adaptive_learning.observe(
                observation_trace,
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
            decision = self.metacognitive_controller.apply(
                adaptive_result.metacognition,
                decision,
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
            derived_research_plan,
            None,
            (),
            None,
            adaptive_result,
            language_check,
            language_corroboration,
        )

    def execute_derived_research(
        self,
        state: ResearchCognitiveState,
        *,
        executor: DerivedResearchExecutor | None = None,
    ) -> DerivedResearchResult | None:
        """Execute only the explicit bounded derived-research plan."""
        if state.derived_research_plan is None:
            return None
        return (executor or DerivedResearchExecutor()).execute(state.derived_research_plan)

    def reassess_after_derived_research(
        self,
        state: ResearchCognitiveState,
        *,
        executor: DerivedResearchExecutor | None = None,
        max_hypotheses: int = 3,
    ) -> ResearchCognitiveState:
        """Verify fresh derived evidence, then re-enter the normal loop."""
        result = self.execute_derived_research(state, executor=executor)
        if result is None:
            return state

        verifier = BoundedMultiSourceVerifier()
        verifications: list[VerificationResult] = []
        annotated = list(result.evidence)

        for hypothesis in state.derived_hypotheses:
            verification = verifier.verify_evidence(hypothesis.claim, result.evidence)
            verifications.append(verification)
            support_by_provenance = {
                row["provenance"]: row["support"] for row in verification.trace
            }
            for index, item in enumerate(annotated):
                support = support_by_provenance.get(item.provenance)
                if support not in {"supports", "contradicts"}:
                    continue
                annotated[index] = type(item)(
                    source=item.source,
                    claim=item.claim,
                    kind=item.kind,
                    provenance=item.provenance,
                    confidence=item.confidence,
                    passage=item.passage,
                    support=support,
                    retrieved_at=item.retrieved_at,
                )

        refreshed = self.initialize(
            state.plan.main_question,
            evidence=annotated,
            queries_used=result.queries_used,
            sources_used=result.sources_used,
            max_hypotheses=max_hypotheses,
        )
        return ResearchCognitiveState(
            refreshed.plan,
            refreshed.hypotheses,
            refreshed.critic,
            refreshed.synthesis,
            refreshed.decision,
            refreshed.evidence_ledger,
            refreshed.joint_inferences,
            refreshed.derived_hypotheses,
            refreshed.derived_research_plan,
            result,
            tuple(verifications),
            None,
            refreshed.adaptive_learning,
            refreshed.language_check,
            refreshed.language_corroboration,
        )

    def reassess_after_invalidation(
        self,
        state: ResearchCognitiveState,
        *,
        invalidated_evidence_id: str,
        target_node_id: str,
        research_question: str,
        loop: ReEvaluationLoop | None = None,
        strategy: str = "research",
        prior_experiences: tuple[Experience, ...] = (),
    ) -> ResearchCognitiveState:
        """Re-enter research and feed the outcome into bounded learning."""
        cycle = (loop or ReEvaluationLoop()).run(
            state.evidence_ledger,
            invalidated_evidence_id=invalidated_evidence_id,
            target_node_id=target_node_id,
            research_question=research_question,
        )
        parent_experience = (
            state.adaptive_learning.experience
            if state.adaptive_learning is not None
            else None
        )
        cycle_id = f"reeval:{invalidated_evidence_id}:{target_node_id}"
        context_key = ""
        context_conditions: tuple[tuple[str, str], ...] = ()
        if parent_experience is not None:
            context_key = parent_experience.context_key
            context_conditions = parent_experience.context_conditions
        cycle_trace = ReEvaluationLearningAdapter().to_trace(
            cycle,
            cycle_id=cycle_id,
            strategy=strategy,
            context_key=context_key,
            context_conditions=context_conditions,
            parent_cycle_id=(
                parent_experience.source_cycle_id
                if parent_experience is not None
                else None
            ),
            parent_lineage=(
                parent_experience.lineage
                if parent_experience is not None
                else ()
            ),
        )
        history = prior_experiences
        if state.adaptive_learning is not None:
            history = (*history, state.adaptive_learning.experience)
        adaptive_result = self.adaptive_learning.observe(
            cycle_trace,
            strategy=strategy,
            prior_experiences=history,
        )
        if self.memory is not None and adaptive_result.experience is not None and (
            adaptive_result.experience.context_key
            or adaptive_result.experience.context_conditions
        ):
            observed = adaptive_result.experience
            self.memory.save_experience_observation(
                source_cycle_id=observed.source_cycle_id,
                outcome=observed.outcome,
                failure_class=observed.failure_class,
                strategy=observed.strategy,
                lesson=observed.lesson,
                safe_to_reuse=observed.safe_to_reuse,
                factual_status=observed.factual_status,
                context_key=observed.context_key,
                context_conditions=observed.context_conditions,
                parent_cycle_id=observed.parent_cycle_id,
                lineage=observed.lineage,
            )

        if cycle.research_result is None:
            return ResearchCognitiveState(
                state.plan,
                state.hypotheses,
                state.critic,
                state.synthesis,
                state.decision,
                state.evidence_ledger,
                state.joint_inferences,
                state.derived_hypotheses,
                state.derived_research_plan,
                state.derived_research_result,
                state.derived_verifications,
                cycle,
                adaptive_result,
                state.language_check,
                state.language_corroboration,
            )

        fresh_evidence = cycle.research_result.evidence
        refreshed = self.initialize(
            state.plan.main_question,
            evidence=fresh_evidence,
            queries_used=cycle.research_result.queries_used,
            sources_used=cycle.research_result.sources_used,
            max_hypotheses=len(state.hypotheses),
        )

        for item in fresh_evidence:
            evidence_id = state.evidence_ledger.evidence_id(
                EvidenceLedgerEntry(
                    claim=item.claim,
                    source=item.source,
                    provenance=item.provenance,
                    confidence=item.confidence,
                    passage=item.passage,
                    support=item.support,
                    retrieved_at=item.retrieved_at,
                )
            )
            for hypothesis in state.hypotheses:
                if item.claim.strip() == hypothesis.claim.strip():
                    state.evidence_ledger.graph.add_edge(
                        ProvenanceEdge(
                            evidence_id,
                            hypothesis.id,
                            item.support.strip().lower() or "unclear",
                        )
                    )

        synthesis_id = (
            "SYNTHESIS:re"
            f"{len(state.evidence_ledger.graph.downstream(target_node_id)) + 1}"
        )
        state.evidence_ledger.graph.add_node(
            ProvenanceNode(synthesis_id, "decision_synthesis", refreshed.synthesis.reason)
        )
        for hypothesis in state.hypotheses:
            state.evidence_ledger.graph.add_edge(
                ProvenanceEdge(hypothesis.id, synthesis_id, "informs")
            )
        if cycle.rebuild is not None:
            state.evidence_ledger.graph.add_edge(
                ProvenanceEdge(
                    cycle.rebuild.replacement_node,
                    synthesis_id,
                    "informs",
                )
            )

        return ResearchCognitiveState(
            state.plan,
            state.hypotheses,
            refreshed.critic,
            refreshed.synthesis,
            refreshed.decision,
            state.evidence_ledger,
            refreshed.joint_inferences,
            refreshed.derived_hypotheses,
            refreshed.derived_research_plan,
            state.derived_research_result,
            state.derived_verifications,
            cycle,
            adaptive_result,
            refreshed.language_check,
            refreshed.language_corroboration,
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
        if state.derived_research_plan is not None:
            return tuple(item.question for item in state.derived_research_plan.subquestions)
        unresolved = set(state.critic.unresolved_hypotheses)
        if "H1" in unresolved and len(state.plan.subquestions) >= 3:
            return (state.plan.subquestions[2].question,)
        return tuple(
            hypothesis.claim
            for hypothesis in state.hypotheses
            if hypothesis.id in unresolved
        )


__all__ = ["ResearchCognitiveLoop", "ResearchCognitiveState"]
