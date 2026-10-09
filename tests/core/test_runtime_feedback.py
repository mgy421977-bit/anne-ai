from anne.core.resource_optimizer import RuntimeResourceSnapshot
from anne.core.resource_profile import ResourceProfile
from anne.core.runtime_feedback import RuntimeFeedbackController, RuntimeMeasurement


def test_measure_records_elapsed_time_and_before_after_snapshots() -> None:
    snapshots = iter(
        [
            RuntimeResourceSnapshot(cpu_count=4, cpu_utilization=0.2, memory_total_bytes=100, memory_available_bytes=80),
            RuntimeResourceSnapshot(cpu_count=4, cpu_utilization=0.5, memory_total_bytes=100, memory_available_bytes=60),
        ]
    )
    result, measurement = RuntimeFeedbackController().measure(
        lambda: "ok",
        lambda: next(snapshots),
    )

    assert result == "ok"
    assert measurement.elapsed_seconds >= 0
    assert measurement.cpu_utilization_before == 0.2
    assert measurement.cpu_utilization_after == 0.5
    assert measurement.memory_pressure_increased


def test_feedback_reduces_profile_only_when_pressure_is_measured() -> None:
    profile = ResourceProfile.scaled(capacity=4)
    measurement = RuntimeMeasurement(
        elapsed_seconds=10,
        cpu_utilization_before=0.2,
        cpu_utilization_after=0.5,
        memory_headroom_before=0.8,
        memory_headroom_after=0.7,
    )

    decision = RuntimeFeedbackController.decide(profile, measurement)

    assert decision.status == "REDUCE_LOAD"
    assert decision.profile.cpu_units < profile.cpu_units


def test_latency_alone_does_not_escalate_resources() -> None:
    profile = ResourceProfile.scaled(capacity=2)
    measurement = RuntimeMeasurement(
        elapsed_seconds=10,
        cpu_utilization_before=0.2,
        cpu_utilization_after=0.2,
        memory_headroom_before=0.8,
        memory_headroom_after=0.8,
    )

    decision = RuntimeFeedbackController.decide(
        profile,
        measurement,
        latency_budget_seconds=1,
    )

    assert decision.status == "INVESTIGATE_LATENCY"
    assert decision.profile == profile


def test_invalid_latency_budget_is_rejected() -> None:
    profile = ResourceProfile.minimal()
    measurement = RuntimeMeasurement(0.1, None, None, 1.0, 1.0)

    decision = RuntimeFeedbackController.decide(
        profile,
        measurement,
        latency_budget_seconds=0,
    )

    assert decision.status == "INVALID_BUDGET"
    assert decision.profile == profile
