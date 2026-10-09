"""Bounded runtime feedback from measured execution outcomes.

This module turns elapsed time and before/after host snapshots into explicit,
bounded observations. It does not treat latency as proof of correctness and
does not directly change OS scheduling or grant execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from collections.abc import Callable
from typing import TypeVar

from anne.core.resource_optimizer import RuntimeResourceSnapshot
from anne.core.resource_profile import ResourceProfile

T = TypeVar("T")


@dataclass(frozen=True)
class RuntimeMeasurement:
    elapsed_seconds: float
    cpu_utilization_before: float | None
    cpu_utilization_after: float | None
    memory_headroom_before: float
    memory_headroom_after: float
    outcome: str = "observed"

    @property
    def cpu_pressure_increased(self) -> bool:
        before, after = self.cpu_utilization_before, self.cpu_utilization_after
        return before is not None and after is not None and after > before + 0.10

    @property
    def memory_pressure_increased(self) -> bool:
        return self.memory_headroom_after < self.memory_headroom_before - 0.10


@dataclass(frozen=True)
class FeedbackDecision:
    status: str
    profile: ResourceProfile
    reason: str
    measurement: RuntimeMeasurement


class RuntimeFeedbackController:
    """Use measured runtime feedback to make conservative profile adjustments."""

    def measure(
        self,
        operation: Callable[[], T],
        snapshot: Callable[[], RuntimeResourceSnapshot],
    ) -> tuple[T, RuntimeMeasurement]:
        before = snapshot()
        started = monotonic()
        result = operation()
        elapsed = max(0.0, monotonic() - started)
        after = snapshot()
        return result, RuntimeMeasurement(
            elapsed_seconds=elapsed,
            cpu_utilization_before=before.cpu_utilization,
            cpu_utilization_after=after.cpu_utilization,
            memory_headroom_before=before.memory_headroom,
            memory_headroom_after=after.memory_headroom,
        )

    @staticmethod
    def decide(
        profile: ResourceProfile,
        measurement: RuntimeMeasurement,
        *,
        latency_budget_seconds: float | None = None,
    ) -> FeedbackDecision:
        if latency_budget_seconds is not None and latency_budget_seconds <= 0:
            return FeedbackDecision(
                "INVALID_BUDGET",
                profile,
                "latency budget must be positive",
                measurement,
            )

        pressured = (
            measurement.cpu_pressure_increased
            or measurement.memory_pressure_increased
        )
        over_budget = (
            latency_budget_seconds is not None
            and measurement.elapsed_seconds > latency_budget_seconds
        )

        if pressured:
            reduced = max(1, max(
                profile.cpu_units,
                profile.memory_units,
                profile.reasoning_budget,
            ) - 1)
            return FeedbackDecision(
                "REDUCE_LOAD",
                ResourceProfile.scaled(substrate=profile.substrate, capacity=reduced),
                "measured host pressure increased; reduce the next bounded workload",
                measurement,
            )

        if over_budget:
            # Latency alone does not prove resource starvation. Keep the profile
            # unchanged until a bottleneck is identified by independent signals.
            return FeedbackDecision(
                "INVESTIGATE_LATENCY",
                profile,
                "latency exceeded its budget without measured host pressure",
                measurement,
            )

        return FeedbackDecision(
            "HOLD",
            profile,
            "no measured pressure signal requires a profile change",
            measurement,
        )


__all__ = ["FeedbackDecision", "RuntimeFeedbackController", "RuntimeMeasurement"]
