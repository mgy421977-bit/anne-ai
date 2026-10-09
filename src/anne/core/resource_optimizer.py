"""Runtime resource observation and bounded optimization.

This layer adapts an already planned ResourceProfile to the current execution
environment. It does not control the operating system, reserve hardware,
install drivers, execute external work, or grant authority.

The optimizer treats OS-visible resources as a shared pool and prefers the
highest useful bounded capacity that remains compatible with the planned
minimum. When the host is busy, ANNE can reduce its target allocation rather
than assuming that all machine resources belong to ANNE.
"""

from __future__ import annotations

import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from anne.core.resource_profile import ResourceProfile


@dataclass(frozen=True)
class RuntimeResourceSnapshot:
    """A point-in-time, read-only view of host resource conditions."""

    cpu_count: int = 1
    cpu_utilization: float | None = None
    memory_total_bytes: int | None = None
    memory_available_bytes: int | None = None
    gpu_count: int = 0
    gpu_utilization: float | None = None
    os_present: bool = True

    @property
    def cpu_headroom(self) -> float:
        if self.cpu_utilization is None:
            return 1.0
        return max(0.0, min(1.0, 1.0 - self.cpu_utilization))

    @property
    def memory_headroom(self) -> float:
        if not self.memory_total_bytes or self.memory_available_bytes is None:
            return 1.0
        return max(
            0.0,
            min(1.0, self.memory_available_bytes / self.memory_total_bytes),
        )


@dataclass(frozen=True)
class ResourceOptimization:
    """The optimizer's bounded recommendation."""

    requested_capacity: int
    optimized_capacity: int
    status: str
    reason: str
    snapshot: RuntimeResourceSnapshot

    @property
    def constrained(self) -> bool:
        return self.optimized_capacity < self.requested_capacity


class SystemResourceProbe:
    """Read-only host resource probe with no third-party dependency."""

    def snapshot(self) -> RuntimeResourceSnapshot:
        cpu_count = max(1, os.cpu_count() or 1)
        cpu_utilization: float | None = None

        try:
            loads = os.getloadavg()
            cpu_utilization = max(0.0, min(1.0, loads[0] / cpu_count))
        except (AttributeError, OSError):
            pass

        total = available = None
        meminfo = Path("/proc/meminfo")
        if meminfo.exists():
            values: dict[str, int] = {}
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                key, _, value = line.partition(":")
                if key in {"MemTotal", "MemAvailable"}:
                    with suppress(ValueError, IndexError):
                        values[key] = int(value.strip().split()[0]) * 1024
            total = values.get("MemTotal")
            available = values.get("MemAvailable")

        return RuntimeResourceSnapshot(
            cpu_count=cpu_count,
            cpu_utilization=cpu_utilization,
            memory_total_bytes=total,
            memory_available_bytes=available,
            # GPU discovery remains an explicit environment integration.
            gpu_count=0,
            gpu_utilization=None,
            os_present=True,
        )


class ResourceOptimizer:
    """Optimize a planned profile against current shared host headroom."""

    def optimize(
        self,
        profile: ResourceProfile,
        snapshot: RuntimeResourceSnapshot,
        *,
        target_utilization: float = 0.80,
    ) -> ResourceOptimization:
        target = max(0.10, min(1.0, target_utilization))
        requested = max(
            profile.cpu_units,
            profile.memory_units,
            profile.reasoning_budget,
        )

        cpu_capacity = max(1, int(snapshot.cpu_count * target))
        if snapshot.cpu_utilization is not None:
            cpu_capacity = max(
                1,
                int(snapshot.cpu_count * max(0.0, target - snapshot.cpu_utilization)),
            )

        # ResourceProfile capacity is an abstract bounded unit. Memory is used
        # as a safety constraint when a host exposes it, not as a claim that
        # one capacity unit equals a fixed number of bytes.
        if snapshot.memory_total_bytes and snapshot.memory_available_bytes is not None:
            memory_ratio = snapshot.memory_headroom
            if memory_ratio < 0.10:
                cpu_capacity = min(cpu_capacity, 1)

        optimized = min(requested, cpu_capacity)
        if optimized >= requested:
            return ResourceOptimization(
                requested_capacity=requested,
                optimized_capacity=requested,
                status="OPTIMAL",
                reason="planned capacity fits current host headroom",
                snapshot=snapshot,
            )

        return ResourceOptimization(
            requested_capacity=requested,
            optimized_capacity=optimized,
            status="CONSTRAINED",
            reason=(
                "host resources are shared; allocation was reduced to remain "
                "within the current bounded operating envelope"
            ),
            snapshot=snapshot,
        )

    @staticmethod
    def apply(
        profile: ResourceProfile,
        optimization: ResourceOptimization,
    ) -> ResourceProfile:
        if optimization.optimized_capacity >= optimization.requested_capacity:
            return profile
        return ResourceProfile.scaled(
            substrate=profile.substrate,
            capacity=max(1, optimization.optimized_capacity),
        )


__all__ = [
    "ResourceOptimization",
    "ResourceOptimizer",
    "RuntimeResourceSnapshot",
    "SystemResourceProbe",
]
