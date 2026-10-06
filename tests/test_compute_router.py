from anne.core.compute_router import ComputeEnvironment, ComputeRouter, ExecutionMode
from anne.core.resource_profile import ResourceProfile, Substrate


def test_router_prefers_local_when_local_is_sufficient() -> None:
    profile = ResourceProfile.scaled(capacity=2)
    decision = ComputeRouter().route(
        profile,
        (
            ComputeEnvironment("remote", ExecutionMode.REMOTE_CPU, capacity=4),
            ComputeEnvironment("local", ExecutionMode.LOCAL, capacity=2),
        ),
    )
    assert decision.status == "ROUTED"
    assert decision.selected_environment is not None
    assert decision.selected_environment.id == "local"


def test_router_escalates_to_remote_when_local_is_insufficient() -> None:
    profile = ResourceProfile.scaled(capacity=4)
    decision = ComputeRouter().route(
        profile,
        (
            ComputeEnvironment("local", ExecutionMode.LOCAL, capacity=1),
            ComputeEnvironment("remote-cpu", ExecutionMode.REMOTE_CPU, capacity=4),
        ),
    )
    assert decision.status == "ROUTED"
    assert decision.selected_environment is not None
    assert decision.selected_environment.id == "remote-cpu"


def test_router_defers_when_no_environment_is_sufficient() -> None:
    profile = ResourceProfile.scaled(capacity=8)
    decision = ComputeRouter().route(
        profile,
        (ComputeEnvironment("gpu", ExecutionMode.GPU, capacity=4),),
    )
    assert decision.status == "DEFERRED"
    assert decision.selected_environment is None


def test_router_respects_substrate_boundary() -> None:
    profile = ResourceProfile(substrate=Substrate.QUANTUM, cpu_units=2, memory_units=2, reasoning_budget=2)
    decision = ComputeRouter().route(
        profile,
        (ComputeEnvironment("classical", ExecutionMode.LOCAL, Substrate.CLASSICAL, capacity=8),),
    )
    assert decision.status == "DEFERRED"
