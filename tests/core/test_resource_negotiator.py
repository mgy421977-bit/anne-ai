from anne.core.resource_negotiator import ResourceNegotiator
from anne.core.resource_optimizer import ResourceOptimization, RuntimeResourceSnapshot
from anne.core.resource_profile import ResourceProfile


def _optimization(profile: ResourceProfile) -> ResourceOptimization:
    snapshot = RuntimeResourceSnapshot(
        cpu_count=8,
        cpu_utilization=0.2,
        memory_total_bytes=16_000,
        memory_available_bytes=8_000,
        os_present=True,
    )
    return ResourceOptimization(
        requested_capacity=profile.cpu_units,
        optimized_capacity=profile.cpu_units,
        status="OPTIMAL",
        reason="test",
        snapshot=snapshot,
    )


def test_windows_negotiation_keeps_driver_ownership_with_os(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.resource_negotiator.platform.system", lambda: "Windows")
    profile = ResourceProfile.scaled(capacity=2)
    optimization = _optimization(profile)

    decision = ResourceNegotiator().negotiate(
        profile,
        optimization,
        optimization.snapshot,
    )

    assert decision.status == "NEGOTIATED"
    assert decision.ownership == "shared_with_os"
    assert decision.shared_driver_boundary is True
    assert set(decision.shared_subsystems) >= {"display", "audio", "network", "storage", "usb"}
    assert decision.effective_profile == profile


def test_non_windows_negotiation_remains_host_managed(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.resource_negotiator.platform.system", lambda: "Linux")
    profile = ResourceProfile.minimal()
    optimization = _optimization(profile)

    decision = ResourceNegotiator().negotiate(
        profile,
        optimization,
        optimization.snapshot,
    )

    assert decision.status == "NEGOTIATED"
    assert decision.ownership == "host_managed"
    assert decision.shared_driver_boundary is True
    assert decision.shared_subsystems == ()
