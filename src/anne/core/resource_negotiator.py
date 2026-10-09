"""Adaptive negotiation with a shared operating-system execution substrate.

ANNE does not own Windows resources or drivers. This layer describes the
bounded resource envelope ANNE may use while leaving ownership, scheduling,
device lifetime and driver control with the operating system.

The first implementation is deliberately read-only: it discovers the host
boundary and produces a negotiation decision. Concrete OS controls such as
Windows Job Objects, CPU sets or process priorities remain separate,
capability-gated integrations.
"""
from __future__ import annotations

from dataclasses import dataclass
import platform

from anne.core.resource_optimizer import ResourceOptimization, RuntimeResourceSnapshot
from anne.core.resource_profile import ResourceProfile


@dataclass(frozen=True)
class ResourceNegotiationDecision:
    """A bounded, non-authoritative agreement with the host execution layer."""

    platform_name: str
    ownership: str
    status: str
    effective_profile: ResourceProfile
    shared_driver_boundary: bool
    shared_subsystems: tuple[str, ...]
    reason: str

    @property
    def os_managed(self) -> bool:
        return self.platform_name == "Windows"


class ResourceNegotiator:
    """Keep ANNE inside an OS-shared resource boundary."""

    _WINDOWS_SHARED_SUBSYSTEMS = (
        "display",
        "audio",
        "network",
        "storage",
        "usb",
    )

    def negotiate(
        self,
        profile: ResourceProfile,
        optimization: ResourceOptimization,
        snapshot: RuntimeResourceSnapshot,
    ) -> ResourceNegotiationDecision:
        system = platform.system() or "Unknown"
        if system == "Windows":
            return ResourceNegotiationDecision(
                platform_name=system,
                ownership="shared_with_os",
                status="NEGOTIATED",
                effective_profile=profile,
                shared_driver_boundary=True,
                shared_subsystems=self._WINDOWS_SHARED_SUBSYSTEMS,
                reason=(
                    "ANNE uses the Windows-managed resource and driver boundary; "
                    "no direct driver ownership or host-wide resource claim is made"
                ),
            )

        return ResourceNegotiationDecision(
            platform_name=system,
            ownership="host_managed",
            status="NEGOTIATED",
            effective_profile=profile,
            shared_driver_boundary=bool(snapshot.os_present),
            shared_subsystems=(),
            reason=(
                "ANNE remains inside the detected host resource boundary; "
                "no direct operating-system resource control is requested"
            ),
        )


__all__ = ["ResourceNegotiationDecision", "ResourceNegotiator"]
