"""Bounded coordinator connecting gap detection, experience and adaptation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from anne.core.trace import CycleTrace
from anne.learning.contextual_strategy import (
    ContextualStrategyChoice,
    ContextualStrategySelector,
    StrategyContext,
)
from anne.learning.experience_learning import Experience, ExperienceLearner
from anne.learning.information_gap import InformationGap, InformationGapDetector
from anne.learning.metacognition import Metacognition, MetacognitiveAssessment
from anne.learning.mitos_experience import MitosExperienceAdapter
from anne.learning.strategy_adaptation import StrategyAdapter, StrategyDecision
from anne.learning.strategy_outcome import StrategyOutcome, StrategyOutcomeEvaluator
from anne.learning.strategy_recovery import StrategyRecovery, StrategyRecoveryEvaluator


@dataclass(frozen=True)
class AdaptiveLearningResult:
    information_gap: InformationGap
    experience: Experience
    strategy: StrategyDecision
    trace: CycleTrace
    metacognition: MetacognitiveAssessment
    strategy_outcome: StrategyOutcome
    strategy_recovery: StrategyRecovery
    contextual_choice: ContextualStrategyChoice


class AdaptiveLearningCoordinator:
    """Turn observed cycle outcomes into bounded next-step guidance."""

    def __init__(
        self,
        *,
        gap_detector: InformationGapDetector | None = None,
        experience_learner: ExperienceLearner | None = None,
        strategy_adapter: StrategyAdapter | None = None,
        strategy_outcome_evaluator: StrategyOutcomeEvaluator | None = None,
        strategy_recovery_evaluator: StrategyRecoveryEvaluator | None = None,
        contextual_selector: ContextualStrategySelector | None = None,
    ) -> None:
        self.gap_detector = gap_detector or InformationGapDetector()
        self.experience_learner = experience_learner or ExperienceLearner()
        self.strategy_adapter = strategy_adapter or StrategyAdapter()
        self.strategy_outcome_evaluator = (
            strategy_outcome_evaluator or StrategyOutcomeEvaluator()
        )
        self.strategy_recovery_evaluator = (
            strategy_recovery_evaluator or StrategyRecoveryEvaluator()
        )
        self.contextual_selector = contextual_selector or ContextualStrategySelector()

    def observe(
        self,
        trace: CycleTrace,
        *,
        strategy: str,
        prior_experiences: tuple[Experience, ...] = (),
        mitos_outcomes: Sequence[ExperienceRecord] = (),
        mitos_failure_classes: Mapping[str, str] | None = None,
    ) -> AdaptiveLearningResult:
        metacognition = Metacognition().assess(trace)
        gap = self.gap_detector.detect(trace)
        experience = self.experience_learner.from_trace(trace, strategy=strategy)

        mitos_experiences: list[Experience] = []
        if mitos_outcomes and (experience.context_key or experience.context_conditions):
            failure_classes = mitos_failure_classes or {}
            adapter = MitosExperienceAdapter()
            for record in mitos_outcomes:
                observed = adapter.to_experience(
                    record,
                    strategy=strategy,
                    failure_class=failure_classes.get(record.hypothesis_id, "unknown"),
                    context_key=experience.context_key,
                )
                if (
                    observed is not None
                    and observed.context_conditions == experience.context_conditions
                ):
                    mitos_experiences.append(observed)

        experiences = (*prior_experiences, *mitos_experiences, experience)

        decision = self.strategy_adapter.adapt(
            strategy,
            experiences,
            context_key=experience.context_key or None,
            context_conditions=experience.context_conditions,
        )
        contextual_choice = self.contextual_selector.select(
            StrategyContext(
                experience.failure_class,
                experience.context_key,
                experience.context_conditions,
            ),
            experiences,
            tuple(
                dict.fromkeys(
                    (strategy, decision.strategy, *(item.strategy for item in experiences))
                )
            ),
        )
        if (
            decision.action != "ABSTAIN"
            and (experience.context_key or experience.context_conditions)
            and contextual_choice.selected_by_observation
            and contextual_choice.candidates
            and contextual_choice.candidates[0].successes > 0
            and contextual_choice.strategy != decision.strategy
        ):
            decision = StrategyDecision(
                "KEEP" if contextual_choice.strategy == strategy else "CHANGE",
                contextual_choice.strategy,
                "selected_from_observed_exact_context_outcomes",
                contextual_choice.candidates[0].source_cycle_ids
                if contextual_choice.candidates
                else (),
            )
        strategy_outcome = self.strategy_outcome_evaluator.evaluate(
            decision, experiences
        )
        strategy_recovery = self.strategy_recovery_evaluator.evaluate(
            strategy, experiences
        )

        learning = dict(trace.learning)
        learning.update({
            "metacognition": {
                "known": metacognition.known,
                "unknown": metacognition.unknown,
                "evidence_basis": metacognition.evidence_basis,
                "assumptions": metacognition.assumptions,
                "decision_dependencies": metacognition.decision_dependencies,
                "recalibration_triggers": metacognition.recalibration_triggers,
                "evaluation_status": metacognition.evaluation_status,
                "research_required": metacognition.research_required,
                "research_reason": metacognition.research_reason,
                "requires_review": metacognition.requires_review,
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
                "parent_cycle_id": experience.parent_cycle_id,
                "lineage": list(experience.lineage),
            },
            "strategy_lineage": {
                "source_cycle_id": experience.source_cycle_id,
                "parent_cycle_id": experience.parent_cycle_id,
                "lineage": list(experience.lineage),
                "strategy": decision.strategy,
            },
            "strategy_adaptation": {
                "action": decision.action,
                "strategy": decision.strategy,
                "reason": decision.reason,
                "source_cycle_ids": decision.source_cycle_ids,
            },
            "strategy_outcome": strategy_outcome.as_dict(),
            "strategy_recovery": strategy_recovery.as_dict(),
            "contextual_strategy": {
                "strategy": contextual_choice.strategy,
                "reason": contextual_choice.reason,
                "selected_by_observation": contextual_choice.selected_by_observation,
            },
        })
        enriched_trace = replace(trace, learning=learning)
        return AdaptiveLearningResult(
            gap,
            experience,
            decision,
            enriched_trace,
            metacognition,
            strategy_outcome,
            strategy_recovery,
            contextual_choice,
        )


__all__ = ["AdaptiveLearningCoordinator", "AdaptiveLearningResult"]
