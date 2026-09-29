"""Bounded strategy performance and rollback guidance.

Performance is observational only. Repeated failure of a changed strategy may
request rollback to the immediately preceding strategy; it never changes
truth, evidence, authority, or execution policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from anne.learning.experience_learning import Experience


class StrategyRecoveryAction(StrEnum):
    KEEP = "keep"
    ROLLBACK = "rollback"
    ABSTAIN = "abstain"
    INSUFFICIENT_OBSERVATION = "insufficient_observation"


@dataclass(frozen=True)
class StrategyRecovery:
    action: StrategyRecoveryAction
    strategy: str
    source_cycle_ids: tuple[str, ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "strategy": self.strategy,
            "source_cycle_ids": list(self.source_cycle_ids),
            "reason": self.reason,
        }


class StrategyRecoveryEvaluator:
    """Choose bounded rollback guidance from an exact context and lineage."""

    def __init__(self, *, window: int = 4, failure_threshold: int = 2) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if failure_threshold < 2:
            raise ValueError("failure_threshold must be >= 2")
        self.window = window
        self.failure_threshold = failure_threshold

    @staticmethod
    def _same_lineage(previous: Experience, latest: Experience) -> bool:
        return (
            previous.source_cycle_id in latest.lineage
            or latest.parent_cycle_id == previous.source_cycle_id
        )

    def evaluate(
        self,
        current_strategy: str,
        experiences: tuple[Experience, ...],
    ) -> StrategyRecovery:
        recent = experiences[-self.window :]
        if not recent:
            return StrategyRecovery(
                StrategyRecoveryAction.INSUFFICIENT_OBSERVATION,
                current_strategy,
                reason="no_experience_observed",
            )

        current = [item for item in recent if item.strategy == current_strategy]
        if len(current) < self.failure_threshold:
            return StrategyRecovery(
                StrategyRecoveryAction.INSUFFICIENT_OBSERVATION,
                current_strategy,
                tuple(item.source_cycle_id for item in current),
                "not_enough_observations_for_rollback",
            )

        latest = current[-1]
        same_context = [
            item
            for item in current
            if item.context_fingerprint == latest.context_fingerprint
        ]
        if len(same_context) < self.failure_threshold:
            return StrategyRecovery(
                StrategyRecoveryAction.INSUFFICIENT_OBSERVATION,
                current_strategy,
                tuple(item.source_cycle_id for item in same_context),
                "not_enough_same_context_observations_for_rollback",
            )

        if not all(
            item.outcome == "FAILURE"
            for item in same_context[-self.failure_threshold :]
        ):
            return StrategyRecovery(
                StrategyRecoveryAction.KEEP,
                current_strategy,
                tuple(item.source_cycle_id for item in same_context),
                "recent_strategy_has_not_repeatedly_failed_in_same_context",
            )

        prior = [
            item
            for item in recent
            if item.strategy != current_strategy
            and item.outcome == "FAILURE"
            and item.context_fingerprint == latest.context_fingerprint
            and self._same_lineage(item, latest)
        ]
        if not prior:
            return StrategyRecovery(
                StrategyRecoveryAction.ABSTAIN,
                "reassess_without_assuming_cause",
                tuple(
                    item.source_cycle_id
                    for item in same_context[-self.failure_threshold :]
                ),
                "no_prior_strategy_in_same_explicit_context_lineage",
            )

        previous = prior[-1]
        return StrategyRecovery(
            StrategyRecoveryAction.ROLLBACK,
            previous.strategy,
            tuple(
                item.source_cycle_id
                for item in same_context[-self.failure_threshold :]
            ),
            "current_strategy_repeatedly_failed; "
            "rollback_to_prior_observed_strategy_in_same_context_lineage",
        )


__all__ = ["StrategyRecovery", "StrategyRecoveryAction", "StrategyRecoveryEvaluator"]
