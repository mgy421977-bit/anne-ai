from anne.core.resource_optimizer import (
    ResourceOptimizer,
    RuntimeResourceSnapshot,
    SystemResourceProbe,
)
from anne.core.resource_profile import ResourceProfile


def test_optimizer_preserves_planned_capacity_when_host_has_headroom():
    profile = ResourceProfile.scaled(capacity=2)
    snapshot = RuntimeResourceSnapshot(
        cpu_count=8,
        cpu_utilization=0.10,
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=12 * 1024**3,
    )

    result = ResourceOptimizer().optimize(profile, snapshot)

    assert result.status == "OPTIMAL"
    assert result.optimized_capacity == 2
    assert not result.constrained


def test_optimizer_detects_shared_host_pressure():
    profile = ResourceProfile.scaled(capacity=4)
    snapshot = RuntimeResourceSnapshot(
        cpu_count=8,
        cpu_utilization=0.75,
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )

    result = ResourceOptimizer().optimize(profile, snapshot)

    assert result.status == "CONSTRAINED"
    assert result.optimized_capacity < result.requested_capacity


def test_probe_is_read_only_and_returns_bounded_snapshot():
    snapshot = SystemResourceProbe().snapshot()

    assert snapshot.cpu_count >= 1
    assert 0.0 <= snapshot.cpu_headroom <= 1.0
    assert 0.0 <= snapshot.memory_headroom <= 1.0
