from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.cognitive_state import CognitiveState
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.learning.critic_loop import LoopDecision


class _StubOrchestrator:
    def run(self, raw_input: str, **_: object) -> OrchestrationResult:
        state = CognitiveState(
            raw_input=raw_input,
            intent="answer",
            requires_evidence=True,
            context_map={
                "intent": "answer",
                "requires_evidence": True,
                "verification_status": "VERIFIED",
                "verification_sources": ("synthetic-source",),
            },
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


class _StubCriticLoop:
    def decide(self, *_: object, **__: object) -> LoopDecision:
        return LoopDecision(
            action="REVIEW",
            reason="synthetic baseline decision",
            research_allowed=True,
        )


def _loop(tmp_path) -> DecisionLoop:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    loop.orchestrator = _StubOrchestrator()
    loop.research_loop.critic_loop = _StubCriticLoop()
    return loop


def test_decision_loop_reuses_learning_in_same_explicit_context(tmp_path) -> None:
    loop = _loop(tmp_path)

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
    assert second.research_state.decision.action == "RESEARCH"
    assert second.research_state.decision.research_allowed is True


def test_decision_loop_does_not_transfer_learning_across_context(tmp_path) -> None:
    loop = _loop(tmp_path)

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
    assert isolated.research_state.decision.action == "REVIEW"
