"""Convert re-evaluation outcomes into bounded learning observations.

The adapter reuses the canonical trace -> experience -> strategy path. It does
not create truth, authority, or action permissions from a re-evaluation result.
"""

from __future__ import annotations

from anne.core.trace import CycleTrace
from anne.learning.reevaluation_loop import ReEvaluationCycleResult


class ReEvaluationLearningAdapter:
    """Turn one re-evaluation cycle into an observable learning trace."""

    def to_trace(
        self,
        cycle: ReEvaluationCycleResult,
        *,
        cycle_id: str,
        strategy: str = "research",
    ) -> CycleTrace:
        verification_status = (
            ""
            if cycle.verification is None
            else cycle.verification.status.value
        ).upper()

        if verification_status == "CONFLICTING":
            status = "BOUNDED"
            stop_reason = "reevaluation_conflict"
            decision_status = "REVIEW"
        elif verification_status == "REFUTED":
            status = "BOUNDED"
            stop_reason = "reevaluation_refuted"
            decision_status = "REVIEW"
        elif cycle.reactivated:
            status = "SUCCESS"
            stop_reason = "reevaluation_verified"
            decision_status = "REACTIVATED"
        elif cycle.research_result is not None and not cycle.research_result.evidence:
            status = "BOUNDED"
            stop_reason = "reevaluation_insufficient_evidence"
            decision_status = "REVIEW"
        elif verification_status == "UNVERIFIED":
            status = "BOUNDED"
            stop_reason = "reevaluation_unverified"
            decision_status = "REVIEW"
        elif cycle.research_result is not None:
            status = "BOUNDED"
            stop_reason = "reevaluation_insufficient_evidence"
            decision_status = "REVIEW"
        else:
            status = "BOUNDED"
            stop_reason = "reevaluation_not_researched"
            decision_status = "REVIEW"

        verification = (
            {}
            if cycle.verification is None
            else cycle.verification.as_dict()
        )
        return CycleTrace(
            cycle_id=cycle_id,
            status=status,
            stage_trace=("INVALIDATION", "RESEARCH", "VERIFICATION"),
            stop_reason=stop_reason,
            verification=verification,
            decision={
                "status": decision_status,
                "strategy": strategy,
            },
            re_evaluation=cycle.as_dict(),
        )


__all__ = ["ReEvaluationLearningAdapter"]
