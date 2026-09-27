from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from anne.learning.critic_loop import CriticLoopController, LoopDecision
from anne.learning.evidence import EvidenceItem
from anne.learning.hypothesis import CriticResult, Hypothesis, HypothesisEngine
from anne.learning.hypothesis_bridge import EvidenceHypothesisBridge
from anne.learning.research_planner import ResearchPlan, ResearchPlanner


@dataclass(frozen=True)
class ResearchCognitiveState:
    plan: ResearchPlan
    hypotheses: tuple[Hypothesis, ...]
    critic: CriticResult
    decision: LoopDecision


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
        critic = EvidenceHypothesisBridge().assess(hypotheses, evidence)
        decision = self.critic_loop.decide(
            critic,
            queries_used=queries_used,
            max_queries=plan.stop_conditions.max_queries,
            sources_used=sources_used,
            max_sources=plan.stop_conditions.max_sources,
        )
        return ResearchCognitiveState(plan, hypotheses, critic, decision)

    @staticmethod
    def next_research_questions(
        state: ResearchCognitiveState,
    ) -> tuple[str, ...]:
        """Return bounded research prompts for unresolved hypotheses."""
        if state.decision.action != "RESEARCH":
            return ()
        unresolved = set(state.critic.unresolved_hypotheses)
        return tuple(
            hypothesis.claim
            for hypothesis in state.hypotheses
            if hypothesis.id in unresolved
        )


__all__ = ["ResearchCognitiveLoop", "ResearchCognitiveState"]
