"""Bounded coordinator connecting gap detection, experience and adaptation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from anne.core.trace import CycleTrace
from anne.learning.experience_learning import Experience, ExperienceLearner\nfrom anne.learning.metacognition import Metacognition, MetacognitiveAssessment
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
        metacognition = Metacognition().assess(trace)\n        gap = self.gap_detector.detect(trace)
        experience = self.experience_learner.from_trace(trace, strategy=strategy)
        experiences = (*prior_experiences, experience)

        if gap.present and "evidence" in gap.categories:
            decision = StrategyDecision(
                "RESEARCH",
                "seek_fresh_independent_evidence",
                "information_gap_requires_fresh_evidence_before_progress",
                tuple(item.source_cycle_id for item in experiences),
            )
        else:
            decision = self.strategy_adapter.adapt(strategy, experiences)

        learning = {\n            "metacognition": {\n                "known": metacognition.known,\n                "unknown": metacognition.unknown,\n                "evidence_basis": metacognition.evidence_basis,\n                "assumptions": metacognition.assumptions,\n                "decision_dependencies": metacognition.decision_dependencies,\n                "recalibration_triggers": metacognition.recalibration_triggers,\n            },\n            "information_gap": {\n                "present": gap.present,\n                "categories": gap.categories,\n                "reason": gap.reason,\n            },\n            "experience": {\n                "source_cycle_id": experience.source_cycle_id,\n                "outcome": experience.outcome,\n                "failure_class": experience.failure_class,\n                "strategy": experience.strategy,\n                "lesson": experience.lesson,\n                "safe_to_reuse": experience.safe_to_reuse,\n                "factual_status": experience.factual_status,\n            },\n            "strategy_adaptation": {\n                "action": decision.action,\n                "strategy": decision.strategy,\n                "reason": decision.reason,\n                "source_cycle_ids": decision.source_cycle_ids,\n            },\n        }\n        enriched_trace = replace(trace, learning=learning)\n        return AdaptiveLearningResult(gap, experience, decision, enriched_trace, metacognition)


__all__ = ["AdaptiveLearningCoordinator", "AdaptiveLearningResult"]
