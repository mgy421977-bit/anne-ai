"""Deterministic strategy selection for ANNE recovery cycles.

Strategy selection is a planning step only. It never executes a retry, grants
execution permission, or promotes failure-derived lessons to evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from anne.core.failure_learning import (
    FailureClass,
    FailureLearningResult,
    FailureLearningStatus,
)


class StrategySelectionStatus(str, Enum):
    SELECTED = "selected"
    MULTIPLE_VALID = "multiple_valid"
    NO_VALID_STRATEGY = "no_valid_strategy"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class StrategyCandidate:
    """A bounded, explicitly available recovery strategy."""

    strategy_id: str
    failure_class: FailureClass
    rationale: str
    source: str = "caller"
    safe: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "failure_class": self.failure_class.value,
            "rationale": self.rationale,
            "source": self.source,
            "safe": self.safe,
        }


@dataclass(frozen=True)
class StrategySelection:
    """Outcome of deterministic strategy filtering/selection."""

    status: StrategySelectionStatus
    selected: StrategyCandidate | None = None
    candidates: tuple[StrategyCandidate, ...] = ()
    rejected: tuple[tuple[str, str], ...] = ()
    next_action: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "selected": self.selected.as_dict() if self.selected else None,
            "candidates": [item.as_dict() for item in self.candidates],
            "rejected": [
                {"strategy_id": strategy_id, "reason": reason}
                for strategy_id, reason in self.rejected
            ],
            "next_action": list(self.next_action),
        }


class StrategySelector:
    """Select only one unambiguous, safe recovery strategy.

    The selector deliberately refuses to rank multiple equally valid
    candidates. A caller must resolve the ambiguity rather than silently
    turning an arbitrary ordering into a decision.
    """

    def select(
        self,
        learning: FailureLearningResult,
        candidates: Iterable[StrategyCandidate],
        *,
        attempted_strategy: str = "",
    ) -> StrategySelection:
        if learning.status in {
            FailureLearningStatus.ABSTAIN,
            FailureLearningStatus.EXHAUSTED,
        }:
            return StrategySelection(
                status=StrategySelectionStatus.ABSTAIN,
                next_action=("Do not retry; require a new safe decision path.",),
            )

        candidate_list = sorted(
            tuple(candidates),
            key=lambda item: (item.strategy_id, item.source),
        )

        valid: list[StrategyCandidate] = []
        rejected: list[tuple[str, str]] = []
        seen: set[str] = set()

        for candidate in candidate_list:
            if candidate.strategy_id in seen:
                rejected.append((candidate.strategy_id, "duplicate_strategy_id"))
                continue
            seen.add(candidate.strategy_id)

            if not candidate.safe:
                rejected.append((candidate.strategy_id, "unsafe_candidate"))
                continue

            if not candidate.strategy_id.strip():
                rejected.append((candidate.strategy_id, "missing_strategy_id"))
                continue

            if (
                candidate.failure_class is not learning.lesson.failure_class
            ):
                rejected.append((candidate.strategy_id, "failure_class_mismatch"))
                continue

            if candidate.strategy_id == attempted_strategy:
                rejected.append((candidate.strategy_id, "same_as_attempted_strategy"))
                continue

            valid.append(candidate)

        if not valid:
            return StrategySelection(
                status=StrategySelectionStatus.NO_VALID_STRATEGY,
                candidates=(),
                rejected=tuple(rejected),
                next_action=(
                    "No safe alternative strategy is available; do not retry unchanged.",
                ),
            )

        if len(valid) > 1:
            return StrategySelection(
                status=StrategySelectionStatus.MULTIPLE_VALID,
                candidates=tuple(valid),
                rejected=tuple(rejected),
                next_action=(
                    "Resolve the valid strategy alternatives explicitly; do not select silently.",
                ),
            )

        selected = valid[0]
        return StrategySelection(
            status=StrategySelectionStatus.SELECTED,
            selected=selected,
            candidates=tuple(valid),
            rejected=tuple(rejected),
            next_action=(
                "Apply the selected strategy only as a new attempt.",
                "Re-verify the new attempt before resubmission.",
            ),
        )


__all__ = [
    "StrategyCandidate",
    "StrategySelection",
    "StrategySelectionStatus",
    "StrategySelector",
]
