from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.runtime import AnneRequest, AnneRuntime


class _FakeOrchestrator:
    def __init__(self, result: OrchestrationResult) -> None:
        self.result = result

    def run(self, *args, **kwargs) -> OrchestrationResult:
        return self.result


class _FakeDecisionLoop:
    def __init__(self) -> None:
        self.learning_context = None
        self.strategy = None

    def run(self, *args, **kwargs):
        self.learning_context = kwargs.get("learning_context")
        self.strategy = kwargs.get("strategy")
        return "decision-result"


def test_decision_loop_produces_trace_with_explicit_learning_context() -> None:
    fail_fast = FailFastResult(True, "ok")
    state = SimpleNamespace(
        output={"verdict": "REVIEW", "action": "REVIEW", "reason": "human review"},
        action="REVIEW",
        context_map={"verification_status": "unverified"},
        ethic_score=None,
    )
    orchestration = OrchestrationResult(
        status="BOUNDED",
        fail_fast=fail_fast,
        state=state,
        selection=None,
        stage_trace=("FAIL_FAST", "DUY", "SELECT"),
        reason="human review",
        retry_count=0,
        lineage=("or_test",),
        stop_reason="agency_review",
    )
    loop = DecisionLoop.__new__(DecisionLoop)
    loop.orchestrator = _FakeOrchestrator(orchestration)

    result = loop.run(
        "test",
        learning_context={
            "key": "web_research",
            "conditions": {"source_count": 2},
        },
    )

    assert result.trace is not None
    assert result.trace.learning["context"]["key"] == "web_research"
    assert result.trace.learning["context"]["conditions"]["source_count"] == 2
    assert result.trace.verification["verification_status"] == "unverified"


def test_decision_loop_does_not_fabricate_learning_context() -> None:
    fail_fast = FailFastResult(True, "ok")
    state = SimpleNamespace(
        output={"verdict": "REVIEW", "action": "REVIEW", "reason": "review"},
        action="REVIEW",
        context_map={"intent_confidence": 0.99},
        ethic_score=None,
    )
    orchestration = OrchestrationResult(
        status="BOUNDED",
        fail_fast=fail_fast,
        state=state,
        selection=None,
        stage_trace=("FAIL_FAST", "DUY"),
        reason="review",
        lineage=("or_test_2",),
        stop_reason="bounded",
    )
    loop = DecisionLoop.__new__(DecisionLoop)
    loop.orchestrator = _FakeOrchestrator(orchestration)

    result = loop.run("test")

    assert result.trace is not None
    assert "context" not in result.trace.learning
    assert "metacognition" in result.trace.learning


def test_runtime_passes_explicit_learning_context_to_decision_loop() -> None:
    loop = _FakeDecisionLoop()
    runtime = AnneRuntime(decision_loop=loop)
    request = AnneRequest(
        text="test",
        learning_context={
            "key": "web_research",
            "conditions": {"freshness": "current"},
        },
    )

    assert runtime.handle(request) == "decision-result"
    assert loop.learning_context == {
        "key": "web_research",
        "conditions": {"freshness": "current"},
    }


def test_runtime_request_preserves_explicit_selected_strategy() -> None:
    loop = _FakeDecisionLoop()
    runtime = AnneRuntime(decision_loop=loop)
    request = AnneRequest(text="test", strategy="recheck_independent_evidence")

    assert runtime.handle(request) == "decision-result"
    assert loop.strategy == "recheck_independent_evidence"
