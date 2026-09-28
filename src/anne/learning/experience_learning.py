"""Bounded extraction of reusable experience from canonical traces.

Experience is an observation about a prior cycle, not a new source of truth.
It is deliberately marked non-reusable until a separate strategy gate permits
reuse under the current conditions.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.self_correction import FailureClass, SelfCorrectionPlanner
from anne.core.trace import CycleTrace


@dataclass(frozen=True)
class Experience:
    source_cycle_id: str
    outcome: str
    failure_class: str
    strategy: str
    lesson: str
    safe_to_reuse: bool
    factual_status: str


class ExperienceLearner:
    """Convert observed traces into bounded, non-authoritative experience."""

    def __init__(self, planner: SelfCorrectionPlanner | None = None) -> None:
        self.planner = planner or SelfCorrectionPlanner()

    def from_trace(self, trace: CycleTrace, *, strategy: str = "") -> Experience:
        reason = trace.stop_reason or ""
        if trace.errors:
            reason = f"{reason} " + " ".join(
                str(error.get("reason", "")) for error in trace.errors
            )

        failure_class = self.planner.classify(trace.stop_reason, reason)
        outcome = (
            "SUCCESS"
            if trace.status.upper() in {"EXECUTED", "SUCCESS"} and not trace.errors
            else "FAILURE"
        )

        if outcome == "SUCCESS":
            failure_class = FailureClass.UNKNOWN

        factual_status = str(trace.verification.get("status", "UNVERIFIED")).upper()
        lesson = (
            f"Observed {outcome.lower()} for strategy '{strategy or 'unspecified'}'; "
            "do not promote this observation to truth."
        )
        return Experience(
            source_cycle_id=trace.cycle_id,
            outcome=outcome,
            failure_class=failure_class.value,
            strategy=strategy,
            lesson=lesson,
            safe_to_reuse=False,
            factual_status=factual_status,
        )


__all__ = ["Experience", "ExperienceLearner"]
