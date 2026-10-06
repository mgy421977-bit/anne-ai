"""Bounded execution-environment routing for ANNE.

The router chooses an execution *target* from an explicit environment
snapshot. It never provisions infrastructure, executes external work, grants
authority, or turns computational capacity into epistemic evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from anne.core.resource_profile import ResourceProfile, Substrate


class ExecutionMode(StrEnum):
    LOCAL = "local"
    REMOTE_CPU = "remote_cpu"
    GPU = "gpu"
    HPC = "hpc"
    SPECIALIZED = "specialized"


@dataclass(frozen=True)
class ComputeEnvironment:
    id: str
    mode: ExecutionMode
    substrate: Substrate = Substrate.CLASSICAL
    capacity: int = 1
    available: bool = True
    cost: float = 0.0
    latency: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("environment capacity must be positive")
        if self.cost < 0 or self.latency < 0:
            raise ValueError("cost and latency must be non-negative")


@dataclass(frozen=True)
class RouteDecision:
    required_capacity: int
    selected_environment: ComputeEnvironment | None
    status: str
    reason: str

    @property
    def executable(self) -> bool:
        return self.status == "ROUTED" and self.selected_environment is not None


class ComputeRouter:
    """Select the minimum available execution environment without executing it."""

    _MODE_ORDER = {
        ExecutionMode.LOCAL: 0,
        ExecutionMode.REMOTE_CPU: 1,
        ExecutionMode.GPU: 2,
        ExecutionMode.HPC: 3,
        ExecutionMode.SPECIALIZED: 4,
    }

    def route(
        self,
        profile: ResourceProfile,
        environments: Iterable[ComputeEnvironment] = (),
    ) -> RouteDecision:
        required = max(
            profile.cpu_units,
            profile.memory_units,
            profile.reasoning_budget,
        )
        candidates = [
            item
            for item in environments
            if item.available
            and item.capacity >= required
            and item.substrate == profile.substrate
        ]
        if not candidates:
            return RouteDecision(
                required_capacity=required,
                selected_environment=None,
                status="DEFERRED",
                reason="no available environment satisfies the bounded resource profile",
            )

        selected = min(
            candidates,
            key=lambda item: (
                self._MODE_ORDER[item.mode],
                item.capacity,
                item.cost,
                item.latency,
            ),
        )
        return RouteDecision(
            required_capacity=required,
            selected_environment=selected,
            status="ROUTED",
            reason="minimum sufficient available environment selected",
        )


__all__ = [
    "ComputeEnvironment",
    "ComputeRouter",
    "ExecutionMode",
    "RouteDecision",
]
