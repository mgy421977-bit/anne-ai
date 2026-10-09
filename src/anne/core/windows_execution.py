"""Windows execution planning and explicitly authorized local controls.

This module is the first controlled-execution boundary for ANNE on Windows.
Planning is side-effect free. Applying controls requires explicit authorization
and only uses bounded process-level controls; ANNE never takes ownership of
Windows drivers or the host scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import platform
from typing import Final

from anne.core.resource_profile import ResourceProfile


_BELOW_NORMAL_PRIORITY_CLASS: Final[int] = 0x00004000


@dataclass(frozen=True)
class WindowsExecutionCapabilities:
    """Capabilities discovered without changing process state."""

    windows: bool
    priority_control: bool
    affinity_control: bool
    job_objects: bool

    @property
    def any_control(self) -> bool:
        return self.priority_control or self.affinity_control or self.job_objects


@dataclass(frozen=True)
class WindowsExecutionPlan:
    """A bounded process-control plan; creation has no OS side effects."""

    status: str
    requested_capacity: int
    priority: str | None
    affinity_mask: int | None
    reason: str
    requires_authorization: bool = True


@dataclass(frozen=True)
class WindowsExecutionResult:
    """Result of an explicitly authorized control application."""

    status: str
    applied: tuple[str, ...]
    skipped: tuple[str, ...]
    reason: str


class WindowsExecutionAdapter:
    """Discover and, only when authorized, apply bounded Windows controls."""

    def capabilities(self) -> WindowsExecutionCapabilities:
        if platform.system() != "Windows":
            return WindowsExecutionCapabilities(False, False, False, False)

        kernel32 = ctypes.windll.kernel32
        return WindowsExecutionCapabilities(
            windows=True,
            priority_control=bool(kernel32.SetPriorityClass),
            affinity_control=bool(kernel32.SetProcessAffinityMask),
            job_objects=bool(kernel32.CreateJobObjectW),
        )

    @staticmethod
    def plan(
        profile: ResourceProfile,
        *,
        background: bool = False,
        cpu_mask: int | None = None,
    ) -> WindowsExecutionPlan:
        if platform.system() != "Windows":
            return WindowsExecutionPlan(
                status="UNAVAILABLE",
                requested_capacity=max(
                    profile.cpu_units,
                    profile.memory_units,
                    profile.reasoning_budget,
                ),
                priority=None,
                affinity_mask=None,
                reason="Windows execution controls are unavailable on this platform",
            )

        return WindowsExecutionPlan(
            status="READY",
            requested_capacity=max(
                profile.cpu_units,
                profile.memory_units,
                profile.reasoning_budget,
            ),
            priority="below_normal" if background else "normal",
            affinity_mask=cpu_mask,
            reason=(
                "Plan is side-effect free; explicit execution authorization is "
                "required before applying process controls"
            ),
        )

    def apply(
        self,
        plan: WindowsExecutionPlan,
        *,
        authorized: bool = False,
    ) -> WindowsExecutionResult:
        if plan.status != "READY":
            return WindowsExecutionResult(
                "SKIPPED",
                (),
                ("windows_controls",),
                plan.reason,
            )
        if not authorized:
            return WindowsExecutionResult(
                "DENIED",
                (),
                ("windows_controls",),
                "Execution controls require explicit authorization",
            )
        if platform.system() != "Windows":
            return WindowsExecutionResult(
                "SKIPPED",
                (),
                ("windows_controls",),
                "Platform changed or Windows controls are unavailable",
            )

        kernel32 = ctypes.windll.kernel32
        process = kernel32.GetCurrentProcess()
        applied: list[str] = []
        skipped: list[str] = []

        if plan.priority == "below_normal":
            if kernel32.SetPriorityClass(process, _BELOW_NORMAL_PRIORITY_CLASS):
                applied.append("priority:below_normal")
            else:
                skipped.append("priority")

        if plan.affinity_mask is not None:
            if kernel32.SetProcessAffinityMask(process, ctypes.c_size_t(plan.affinity_mask)):
                applied.append(f"affinity:{plan.affinity_mask:#x}")
            else:
                skipped.append("affinity")

        status = "APPLIED" if applied else "NOOP"
        return WindowsExecutionResult(
            status,
            tuple(applied),
            tuple(skipped),
            "Only explicitly authorized process-level controls were attempted",
        )


__all__ = [
    "WindowsExecutionAdapter",
    "WindowsExecutionCapabilities",
    "WindowsExecutionPlan",
    "WindowsExecutionResult",
]
