"""Bounded decision feedback loop for ANNE.

This module composes Decision Synthesis, METACOG, Failure Learning, and
deterministic Strategy Selection into one explicit review/recovery cycle. It
does not perform an automatic retry and does not promote failure-derived
lessons to evidence or permanent knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from anne.core.decision_synthesis import DecisionSynthesis
from anne.core.failure_learning import (
    FailureLearningEngine,
    FailureLearningResult,
    FailureLearningStatus,
)
from anne.core.metacognition import (
    MetaStatus,
    MetacognitiveEvaluator,
    MetacognitiveReview,
)
from anne.core.strategy_selection import (
    StrategyCandidate,
    StrategySelection,
    StrategySelectionStatus,
    StrategySelector,
)


@dataclass(frozen=True)
class FeedbackCycle:
    """Serializable output of one guarded synthesis/review/learning cycle."""

    review: MetacognitiveReview
    failure_learning: tuple[FailureLearningResult, ...] = ()
    strategy_selection: tuple[StrategySelection, ...] = ()
    retry_allowed: bool = False
    next_action: tuple[str, ...] = ()

    @property
    def strategy_change_required(self) -> bool:
        return any(
            item.status is FailureLearningStatus.STRATEGY_CHANGE_REQUIRED
            for item in self.failure_learning
        )

    @property
    def exhausted(self) -> bool:
        return any(
            item.status is FailureLearningStatus.EXHAUSTED
            for item in self.failure_learning
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "review": self.review.as_dict(),
            "failure_learning": [item.as_dict() for item in self.failure_learning],
            "strategy_selection": [item.as_dict() for item in self.strategy_selection],
            "retry_allowed": self.retry_allowed,
            "strategy_change_required": self.strategy_change_required,
            "exhausted": self.exhausted,
            "next_action": list(self.next_action),
        }


class DecisionFeedbackLoop:
    """Compose bounded review, learning, and explicit strategy selection."""

    def __init__(
        self,
        evaluator: MetacognitiveEvaluator | None = None,
        learner: FailureLearningEngine | None = None,
        selector: StrategySelector | None = None,
    ) -> None:
        self.evaluator = evaluator or MetacognitiveEvaluator()
        self.learner = learner or FailureLearningEngine()
        self.selector = selector or StrategySelector()

    def evaluate(
        self,
        synthesis: DecisionSynthesis,
        *,
        declared_confidence: float | None = None,
        prior_failures: Sequence[Mapping[str, Any]] = (),
        attempted_strategy: str = "",
        retry_index: int = 0,
        max_retries: int | None = None,
        strategy_candidates: Sequence[StrategyCandidate] = (),
    ) -> FeedbackCycle:
        """Review a synthesis and derive bounded recovery signals.

        No retry is executed here. The caller must explicitly submit a new
        attempt after applying the selected strategy and re-verifying it.
        """

        review = self.evaluator.evaluate(
            synthesis,
            declared_confidence=declared_confidence,
        )
        failures = tuple(
            self.learner.learn(
                failure,
                prior_failures=prior_failures,
                attempted_strategy=attempted_strategy,
                retry_index=retry_index,
                max_retries=(
                    self.learner.planner.MAX_RETRIES
                    if max_retries is None
                    else max_retries
                ),
            )
            for failure in synthesis.failure_trace
        )

        selections: list[StrategySelection] = []
        for learning in failures:
            if strategy_candidates:
                candidates = strategy_candidates
            else:
                candidates = (
                    StrategyCandidate(
                        strategy_id=learning.lesson.recommended_strategy,
                        failure_class=learning.lesson.failure_class,
                        rationale=(
                            "Derived from the bounded failure-learning signal; "
                            "requires re-verification before use."
                        ),
                        source="failure_learning",
                    ),
                )
            selections.append(
                self.selector.select(
                    learning,
                    candidates,
                    attempted_strategy=attempted_strategy,
                )
            )

        retry_blocked = (
            review.status is MetaStatus.ABSTAIN
            or any(
                item.status
                in {
                    FailureLearningStatus.ABSTAIN,
                    FailureLearningStatus.EXHAUSTED,
                    FailureLearningStatus.STRATEGY_CHANGE_REQUIRED,
                }
                for item in failures
            )
            or any(
                item.status is not StrategySelectionStatus.SELECTED
                for item in selections
            )
        )
        retry_allowed = (
            bool(failures)
            and review.status is MetaStatus.REVIEW
            and not retry_blocked
        )

        actions = list(review.next_action)
        for item in failures:
            for action in item.next_action:
                if action not in actions:
                    actions.append(action)
        for selection in selections:
            for action in selection.next_action:
                if action not in actions:
                    actions.append(action)

        if not synthesis.failure_trace and review.status is MetaStatus.REVIEW:
            actions.append("Provide a new evidence-backed attempt; no automatic retry is performed.")

        if retry_allowed:
            actions.append("Caller must re-verify the next attempt before resubmission.")

        return FeedbackCycle(
            review=review,
            failure_learning=failures,
            strategy_selection=tuple(selections),
            retry_allowed=retry_allowed,
            next_action=tuple(actions),
        )


__all__ = ["DecisionFeedbackLoop", "FeedbackCycle"]
