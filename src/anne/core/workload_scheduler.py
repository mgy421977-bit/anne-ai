"""Bounded local workload scheduling for ANNE.

The scheduler coordinates ANNE-owned background work without assuming
ownership of the host. Interactive/media workloads can reserve a higher
priority while background jobs yield under host pressure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from time import monotonic
from typing import Callable


class WorkloadPriority(IntEnum):
    BACKGROUND = 10
    NORMAL = 20
    HIGH = 30
    INTERACTIVE = 40


@dataclass
class WorkItem:
    id: str
    name: str
    callback: Callable[[], object]
    priority: WorkloadPriority = WorkloadPriority.NORMAL
    estimated_cost: int = 1
    metadata: dict[str, object] = field(default_factory=dict)


class WorkloadScheduler:
    """Small cooperative scheduler for ANNE-local work.

    It does not change OS scheduling policy.  It decides which ANNE-owned
    task should run next and can defer background work when host pressure is
    reported by the resource layer.
    """

    def __init__(self, *, max_queue: int = 64) -> None:
        if max_queue < 1:
            raise ValueError("max_queue must be positive")
        self.max_queue = max_queue
        self._queue: list[WorkItem] = []

    def submit(self, item: WorkItem) -> None:
        if len(self._queue) >= self.max_queue:
            raise RuntimeError("ANNE workload queue is full")
        self._queue.append(item)

    def pending(self) -> tuple[WorkItem, ...]:
        return tuple(self._queue)

    def choose(self, *, host_pressure: float = 0.0) -> WorkItem | None:
        if not self._queue:
            return None
        pressure = max(0.0, min(1.0, host_pressure))
        eligible = [
            item
            for item in self._queue
            if not (pressure >= 0.80 and item.priority == WorkloadPriority.BACKGROUND)
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda item: (int(item.priority), -max(1, item.estimated_cost)),
        )

    def run_next(self, *, host_pressure: float = 0.0) -> object | None:
        item = self.choose(host_pressure=host_pressure)
        if item is None:
            return None
        self._queue.remove(item)
        started = monotonic()
        result = item.callback()
        item.metadata["runtime_seconds"] = monotonic() - started
        return result


__all__ = ["WorkItem", "WorkloadPriority", "WorkloadScheduler"]
