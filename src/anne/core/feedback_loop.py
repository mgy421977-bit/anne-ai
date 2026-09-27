"""Bounded decision feedback loop for ANNE.

This module composes Decision Synthesis, METACOG, and Failure Learning into
one explicit review/recovery cycle. It does not perform an automatic retry and
does not promote failure-derived lessons to evidence or permanent knowledge.
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


@dataclass(frozen=True)
class FeedbackCycle:
    """Serializable output of one guarded synthesis/review/learning cycle."""

    review: MetacognitiveReview
    failure_learning: tuple[FailureLearningResult, ...] = ()
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
            "retry_allowed": self.retry_allowed,
            "strategy_change_required": self.strategy_change_required,
            "exhausted": self.exhausted,
            "next_action": list(self.next_action),
        }


class DecisionFeedbackLoop:
    """Compose bounded metacognitive review with SFT-driven recovery planning."""

    def __init__(
        self,
        evaluator: MetacognitiveEvaluator | None = None,
        learner: FailureLearningEngine | None = None,
    ) -> None:
        self.evaluator = evaluator or MetacognitiveEvaluator()
        self.learner = learner or FailureLearningEngine()

    def evaluate(
        self,
        synthesis: DecisionSynthesis,
        *,
        declared_confidence: float | None = None,
        prior_failures: Sequence[Mapping[str, Any]] = (),
        attempted_strategy: str = "",
        retry_index: int = 0,
        max_retries: int | None = None,
    ) -> FeedbackCycle:
        """Review a synthesis and derive bounded recovery signals.

        No retry is executed here. The caller must explicitly submit a new
        attempt after applying the returned strategy and re-verifying it.
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
        )
        retry_allowed = review.status is MetaStatus.REVIEW and not retry_blocked

        actions = list(review.next_action)
        for item in failures:
            for action in item.next_action:
                if action not in actions:
                    actions.append(action)

        if not synthesis.failure_trace and review.status is MetaStatus.REVIEW:
            actions.append("Provide a new evidence-backed attempt; no automatic retry is performed.")

        if retry_allowed:
            actions.append("Caller must re-verify the next attempt before resubmission.")

        return FeedbackCycle(
            review=review,
            failure_learning=failures,
            retry_allowed=retry_allowed,
            next_action=tuple(actions),
        )


__all__ = ["DecisionFeedbackLoop", "FeedbackCycle"]
