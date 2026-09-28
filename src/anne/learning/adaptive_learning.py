"""Bounded coordinator connecting gap detection, experience and adaptation."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.trace import CycleTrace
from anne.learning.experience_learning import Experience, ExperienceLearner
from anne.learning.information_gap import InformationGap, InformationGapDetector
from anne.learning.strategy_adaptation import StrategyAdapter, StrategyDecision


@dataclass(frozen=True)
class AdaptiveLearningResult:
    information_gap: InformationGap
    experience: Experience
    strategy: StrategyDecision


class AdaptiveLearningCoordinator:
    """Turn observed cycle outcomes into bounded next-step guidance.

    This coordinator observes a completed trace. It does not execute tools,
    grant authority, verify facts, or mutate the safety policy.
    """

    def __init__(
        self,
        *,
        gap_detector: InformationGapDetector | None = None,
        experience_learner: ExperienceLearner | None = None,
        strategy_adapter: StrategyAdapter | None = None,
    ) -> None:
        self.gap_detector = gap_detector or InformationGapDetector()
        self.experience_learner = experience_learner or ExperienceLearner()
        self.strategy_adapter = strategy_adapter or StrategyAdapter()

    def observe(
        self,
        trace: CycleTrace,
        *,
        strategy: str,
        prior_experiences: tuple[Experience, ...] = (),
    ) -> AdaptiveLearningResult:
        gap = self.gap_detector.detect(trace)
        experience = self.experience_learner.from_trace(trace, strategy=strategy)
        experiences = (*prior_experiences, experience)

        if gap.present and experience.failure_class == "evidence_gap":
            decision = self.strategy_adapter.adapt(strategy, experiences)
            if decision.action == "CHANGE":
                decision = StrategyDecision(
                    "RESEARCH",
                    decision.strategy,
                    "information_gap_requires_fresh_evidence_before_progress",
                    decision.source_cycle_ids,
                )
        else:
            decision = self.strategy_adapter.adapt(strategy, experiences)

        return AdaptiveLearningResult(gap, experience, decision)


__all__ = ["AdaptiveLearningCoordinator", "AdaptiveLearningResult"]
