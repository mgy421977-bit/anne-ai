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


def test_research_handoff_does_not_execute_research_implicitly(tmp_path) -> None:
    loop = _loop(tmp_path)

    def fail_if_called(*_: object, **__: object) -> None:
        raise AssertionError("research execution must require an explicit call")

    loop.research_loop.execute_derived_research = fail_if_called  # type: ignore[method-assign]

    loop.run(
        "research question",
        learning_context={"key": "task-a", "conditions": {"mode": "research"}},
        strategy="research",
    )
    second = loop.run(
        "research question",
        learning_context={"key": "task-a", "conditions": {"mode": "research"}},
        strategy="research",
    )

    assert second.research_state is not None
    assert second.research_state.decision.action == "RESEARCH"
    assert second.research_state.decision.research_allowed is True
    assert second.research_state.derived_research_result is None
