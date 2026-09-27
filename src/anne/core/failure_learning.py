"""Bounded failure-learning feedback for ANNE.

This layer turns structured failure traces into explicit lessons and bounded
recovery plans. A failure is never promoted to validated knowledge; the
feedback is a strategy signal that must be re-verified on a later attempt.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence

from anne.core.self_correction import (
    FailureClass,
    ReframePlan,
    SelfCorrectionPlanner,
)


class FailureLearningStatus(StrEnum):
    RECORDED = "RECORDED"
    STRATEGY_CHANGE_REQUIRED = "STRATEGY_CHANGE_REQUIRED"
    EXHAUSTED = "EXHAUSTED"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class FailureLesson:
    """A non-authoritative lesson extracted from a failed attempt."""

    failure_key: str
    failure_class: FailureClass
    cause: str
    attempted_strategy: str
    recommended_strategy: str
    retry_index: int
    max_retries: int
    repeated: bool
    strategy_change_required: bool
    safe_to_reuse: bool = False

    @property
    def validated(self) -> bool:
        """Failure-derived lessons are never validated facts."""

        return False

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failure_class"] = self.failure_class.value
        data["validated"] = False
        return data


@dataclass(frozen=True)
class FailureLearningResult:
    """Structured failure feedback for the next guarded attempt."""

    status: FailureLearningStatus
    lesson: FailureLesson
    reframe_plan: ReframePlan
    next_action: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "lesson": self.lesson.as_dict(),
            "reframe_plan": {
                "original": self.reframe_plan.original,
                "reframed": self.reframe_plan.reframed,
                "failure_class": self.reframe_plan.failure_class.value,
                "retry_index": self.reframe_plan.retry_index,
                "max_retries": self.reframe_plan.max_retries,
                "exhausted": self.reframe_plan.exhausted,
                "signal": asdict(self.reframe_plan.signal)
                | {"failure_class": self.reframe_plan.signal.failure_class.value},
            },
            "next_action": list(self.next_action),
        }


class FailureLearningEngine:
    """Convert SFT records into bounded, non-authoritative strategy feedback."""

    def __init__(self, planner: SelfCorrectionPlanner | None = None) -> None:
        self.planner = planner or SelfCorrectionPlanner()

    def learn(
        self,
        failure: Mapping[str, Any],
        *,
        prior_failures: Sequence[Mapping[str, Any]] = (),
        attempted_strategy: str = "",
        retry_index: int = 0,
        max_retries: int = SelfCorrectionPlanner.MAX_RETRIES,
    ) -> FailureLearningResult:
        if retry_index < 0:
            raise ValueError("retry_index must be non-negative")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_index > max_retries:
            raise ValueError("retry_index cannot exceed max_retries")

        reason = self._reason(failure)
        meta_tag = self._meta_tag(failure)
        failure_key = self._failure_key(failure, reason, meta_tag)
        current_strategy = (
            attempted_strategy.strip()
            or str(failure.get("strategy") or "").strip()
        )

        matching = [
            item
            for item in prior_failures
            if self._failure_key(item, self._reason(item), self._meta_tag(item))
            == failure_key
        ]
        repeated = bool(matching)

        prior_strategies = {
            str(item.get("strategy") or "").strip().casefold()
            for item in matching
            if str(item.get("strategy") or "").strip()
        }
        same_strategy = (
            current_strategy.casefold() in prior_strategies
            if current_strategy
            else repeated
        )
        strategy_change_required = repeated and same_strategy

        plan = self.planner.plan(
            str(failure.get("original") or failure.get("claim") or reason).strip(),
            meta_tag=meta_tag,
            reason=reason,
            retry_index=retry_index,
            max_retries=max_retries,
        )

        lesson = FailureLesson(
            failure_key=failure_key,
            failure_class=plan.failure_class,
            cause=reason or "Cause not established.",
            attempted_strategy=current_strategy or "UNSPECIFIED",
            recommended_strategy=plan.signal.strategy,
            retry_index=retry_index,
            max_retries=max_retries,
            repeated=repeated,
            strategy_change_required=strategy_change_required,
            safe_to_reuse=False,
        )

        if plan.exhausted:
            status = FailureLearningStatus.EXHAUSTED
            next_action = [
                "Do not retry within the bounded budget.",
                "Abstain or return control to a higher-level review path.",
            ]
        elif plan.failure_class in {
            FailureClass.ETHICAL,
            FailureClass.EXECUTION_RISK,
        }:
            status = FailureLearningStatus.ABSTAIN
            next_action = [
                "Do not execute the failed path.",
                "Require a safe alternative or explicit authority review.",
            ]
        elif strategy_change_required:
            status = FailureLearningStatus.STRATEGY_CHANGE_REQUIRED
            next_action = [
                "Do not repeat the failed strategy unchanged.",
                f"Use the bounded strategy: {plan.signal.strategy}.",
            ]
        else:
            status = FailureLearningStatus.RECORDED
            next_action = [
                f"Retry only through the bounded strategy: {plan.signal.strategy}.",
                "Re-verify the result; the failure lesson is not evidence by itself.",
            ]

        return FailureLearningResult(
            status=status,
            lesson=lesson,
            reframe_plan=plan,
            next_action=next_action,
        )

    @staticmethod
    def _reason(failure: Mapping[str, Any]) -> str:
        return str(
            failure.get("reason")
            or failure.get("cause")
            or failure.get("detail")
            or ""
        ).strip()

    @staticmethod
    def _meta_tag(failure: Mapping[str, Any]) -> str:
        return str(
            failure.get("meta_tag")
            or failure.get("failure_class")
            or failure.get("class")
            or ""
        ).strip()

    @classmethod
    def _failure_key(
        cls,
        failure: Mapping[str, Any],
        reason: str,
        meta_tag: str,
    ) -> str:
        explicit_id = str(failure.get("id") or failure.get("failure_id") or "").strip()
        if explicit_id:
            return explicit_id.casefold()
        if reason:
            return reason.casefold()
        if meta_tag:
            return meta_tag.casefold()
        return "unknown_failure"


__all__ = [
    "FailureLearningEngine",
    "FailureLearningResult",
    "FailureLearningStatus",
    "FailureLesson",
]
