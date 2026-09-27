"""Bounded MITOS proposal orchestration.

MITOS is a proposal engine. ANNE remains the selector. This layer makes the
proposal batch explicit, preserves rejected/eligible alternatives for audit,
and never executes a proposal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Sequence

from anne.mythos.candidate import HypothesisCandidate, SelectionResult, TaskMode
from anne.mythos.selection import CandidateSelector


class MitosOrchestrationStatus(StrEnum):
    SELECTED = "selected"
    NO_ELIGIBLE_PROPOSAL = "no_eligible_proposal"
    REVIEW = "review"


@dataclass(frozen=True)
class MitosProposalSet:
    """Immutable proposal batch presented by MITOS to ANNE."""

    candidates: tuple[HypothesisCandidate, ...]
    task_mode: TaskMode
    budget: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_mode": self.task_mode.value,
            "budget": self.budget,
            "candidates": [
                {
                    "id": candidate.id,
                    "goal": candidate.goal,
                    "claim": candidate.claim,
                    "probability": candidate.probability,
                    "evidence_status": candidate.evidence_status,
                    "score_origin": candidate.score_origin,
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True)
class MitosOrchestrationResult:
    status: MitosOrchestrationStatus
    proposals: MitosProposalSet
    selection: SelectionResult | None
    next_action: tuple[str, ...]

    @property
    def selected_candidate(self) -> HypothesisCandidate | None:
        if self.selection is None or not self.selection.accepted:
            return None
        return self.selection.candidate

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "proposals": self.proposals.as_dict(),
            "selection": (
                {
                    "accepted": self.selection.accepted,
                    "reason": self.selection.reason,
                    "score": self.selection.score,
                    "considered": self.selection.considered,
                    "candidate_id": (
                        self.selection.candidate.id
                        if self.selection.candidate
                        else None
                    ),
                }
                if self.selection is not None
                else None
            ),
            "next_action": list(self.next_action),
        }


class MitosOrchestrator:
    """Create a bounded MITOS proposal set and pass it through ANNE's gate."""

    def __init__(
        self,
        selector: CandidateSelector | None = None,
        *,
        max_candidates: int = 8,
    ) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        self.selector = selector or CandidateSelector()
        self.max_candidates = max_candidates

    def evaluate(
        self,
        candidates: Sequence[HypothesisCandidate],
        *,
        task_mode: TaskMode = TaskMode.GENERAL,
        budget: int | None = None,
    ) -> MitosOrchestrationResult:
        limit = self.max_candidates if budget is None else budget
        if limit < 1:
            raise ValueError("budget must be positive")

        bounded = tuple(candidates[:limit])
        proposals = MitosProposalSet(
            candidates=bounded,
            task_mode=task_mode,
            budget=limit,
        )

        if not bounded:
            return MitosOrchestrationResult(
                MitosOrchestrationStatus.NO_ELIGIBLE_PROPOSAL,
                proposals,
                None,
                ("Generate a new bounded proposal set; do not execute.",),
            )

        selection = self.selector.select(bounded, task_mode=task_mode)
        if not selection.accepted:
            return MitosOrchestrationResult(
                MitosOrchestrationStatus.NO_ELIGIBLE_PROPOSAL,
                proposals,
                selection,
                ("No proposal passed the ANNE gate; do not execute a proposal.",),
            )

        return MitosOrchestrationResult(
            MitosOrchestrationStatus.SELECTED,
            proposals,
            selection,
            (
                "Selected proposal remains unexecuted until downstream verification.",
                "Re-verify evidence, safety, and authority before execution.",
            ),
        )


__all__ = [
    "MitosOrchestrationResult",
    "MitosOrchestrationStatus",
    "MitosOrchestration",
    "MitosProposalSet",
]
