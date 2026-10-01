from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.cognitive_state import CognitiveState
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult


class _StubOrchestrator:
    def run(self, raw_input: str, **_: object) -> OrchestrationResult:
        state = CognitiveState(
            raw_input=raw_input,
            intent="answer",
            context_map={},
            action="REVIEW",
            output={
                "verdict": "REVIEW",
                "action": "REVIEW",
                "reason": "fresh evidence required",
            },
        )
        return OrchestrationResult(
            status="BOUNDED",
            fail_fast=FailFastResult(True, "ok"),
            state=state,
            selection=None,
            stage_trace=("FAIL_FAST", "DUY", "BAK"),
            reason="evidence_gap",
            stop_reason="evidence_gap",
        )


def test_decision_loop_reuses_learning_in_same_explicit_context(tmp_path) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    loop.orchestrator = _StubOrchestrator()

    first = loop.run(
        "research question",
        learning_context={"key": "task-a", "conditions": {"mode": "research"}},
        strategy="research",
    )
    second = loop.run(
        "research question",
        learning_context={"key": "task-a", "conditions": {"mode": "research"}},
        strategy="research",
    )

    assert first.research_state is not None
    assert second.research_state is not None
    adaptation = second.research_state.adaptive_learning
    assert adaptation is not None
    assert adaptation.strategy.action == "CHANGE"
    assert adaptation.strategy.strategy == "seek_fresh_independent_evidence"


def test_decision_loop_does_not_transfer_learning_across_context(tmp_path) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    loop.orchestrator = _StubOrchestrator()

    loop.run(
        "research question",
        learning_context={"key": "task-a", "conditions": {"mode": "research"}},
        strategy="research",
    )
    isolated = loop.run(
        "research question",
        learning_context={"key": "task-b", "conditions": {"mode": "research"}},
        strategy="research",
    )

    assert isolated.research_state is not None
    adaptation = isolated.research_state.adaptive_learning
    assert adaptation is not None
    assert adaptation.strategy.action == "KEEP"
    assert adaptation.strategy.strategy == "research"
