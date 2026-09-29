"""Bounded coordinator connecting gap detection, experience and adaptation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from anne.core.trace import CycleTrace
from anne.learning.experience_learning import Experience, ExperienceLearner
from anne.learning.information_gap import InformationGap, InformationGapDetector
from anne.learning.metacognition import Metacognition, MetacognitiveAssessment
from anne.learning.strategy_adaptation import StrategyAdapter, StrategyDecision
from anne.learning.strategy_outcome import StrategyOutcome, StrategyOutcomeEvaluator


@dataclass(frozen=True)
class AdaptiveLearningResult:
    information_gap: InformationGap
    experience: Experience
    strategy: StrategyDecision
    trace: CycleTrace
    metacognition: MetacognitiveAssessment
    strategy_outcome: StrategyOutcome


class AdaptiveLearningCoordinator:
    """Turn observed cycle outcomes into bounded next-step guidance."""

    def __init__(
        self,
        *,
        gap_detector: InformationGapDetector | None = None,
        experience_learner: ExperienceLearner | None = None,
        strategy_adapter: StrategyAdapter | None = None,
        strategy_outcome_evaluator: StrategyOutcomeEvaluator | None = None,
    ) -> None:
        self.gap_detector = gap_detector or InformationGapDetector()
        self.experience_learner = experience_learner or ExperienceLearner()
        self.strategy_adapter = strategy_adapter or StrategyAdapter()
        self.strategy_outcome_evaluator = (
            strategy_outcome_evaluator or StrategyOutcomeEvaluator()
        )

    def observe(
        self,
        trace: CycleTrace,
        *,
        strategy: str,
        prior_experiences: tuple[Experience, ...] = (),
    ) -> AdaptiveLearningResult:
        metacognition = Metacognition().assess(trace)
        gap = self.gap_detector.detect(trace)
        experience = self.experience_learner.from_trace(trace, strategy=strategy)
        experiences = (*prior_experiences, experience)

        decision = self.strategy_adapter.adapt(strategy, experiences)
        strategy_outcome = self.strategy_outcome_evaluator.evaluate(
            decision, experiences
        )

        learning = {
            "metacognition": {
                "known": metacognition.known,
                "unknown": metacognition.unknown,
                "evidence_basis": metacognition.evidence_basis,
                "assumptions": metacognition.assumptions,
                "decision_dependencies": metacognition.decision_dependencies,
                "recalibration_triggers": metacognition.recalibration_triggers,
            },
            "information_gap": {
                "present": gap.present,
                "categories": gap.categories,
                "reason": gap.reason,
            },
            "experience": {
                "source_cycle_id": experience.source_cycle_id,
                "outcome": experience.outcome,
                "failure_class": experience.failure_class,
                "strategy": experience.strategy,
                "lesson": experience.lesson,
                "safe_to_reuse": experience.safe_to_reuse,
                "factual_status": experience.factual_status,
            },
            "strategy_adaptation": {
                "action": decision.action,
                "strategy": decision.strategy,
                "reason": decision.reason,
                "source_cycle_ids": decision.source_cycle_ids,
            },
            "strategy_outcome": strategy_outcome.as_dict(),
        }
        enriched_trace = replace(trace, learning=learning)
        return AdaptiveLearningResult(
            gap,
            experience,
            decision,
            enriched_trace,
            metacognition,
            strategy_outcome,
        )


__all__ = ["AdaptiveLearningCoordinator", "AdaptiveLearningResult"]
