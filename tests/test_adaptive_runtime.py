from types import SimpleNamespace

from anne.core.decision_loop import DecisionResult
from anne.core.trace import CycleTrace
from anne.learning.adaptive_runtime import AdaptiveRuntimeController
from anne.runtime import AnneRuntime


class _FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def run(self, text: str, *, learning_context=None, strategy=None) -> DecisionResult:
        self.calls.append(strategy)
        trace = CycleTrace(
            cycle_id=f"cycle-{len(self.calls)}",
            status="BOUNDED",
            stop_reason="evidence_gap",
            learning={"context": learning_context or {}},
        )
        return DecisionResult(
            status="ABORTED",
            verdict="REVIEW",
            action="REVIEW",
            trace=trace,
        )


def test_adaptive_runtime_carries_selected_strategy_to_next_cycle() -> None:
    runtime = _FakeRuntime()
    controller = AdaptiveRuntimeController(
        runtime, initial_strategy="research", max_experiences=4
    )

    first = controller.run(
        "test",
        learning_context={
            "key": "web_research",
            "conditions": {"source_count": 2},
        },
    )

    assert runtime.calls == ["research"]
    assert first.next_strategy == "research"
    assert len(controller.experiences) == 1


def test_adaptive_runtime_bounds_experience_history() -> None:
    runtime = _FakeRuntime()
    controller = AdaptiveRuntimeController(
        runtime, initial_strategy="research", max_experiences=2
    )

    controller.run("one")
    controller.run("two")
    controller.run("three")

    assert len(controller.experiences) == 2
    assert controller.experiences[0].source_cycle_id == "cycle-2"
    assert controller.experiences[1].source_cycle_id == "cycle-3"


def test_adaptive_runtime_requires_canonical_trace() -> None:
    class NoTraceRuntime:
        def run(self, text: str, *, learning_context=None, strategy=None):
            return SimpleNamespace(trace=None)

    controller = AdaptiveRuntimeController(
        NoTraceRuntime(), initial_strategy="research"
    )

    try:
        controller.run("test")
    except RuntimeError as exc:
        assert "canonical trace" in str(exc)
    else:
        raise AssertionError("expected canonical trace failure")
