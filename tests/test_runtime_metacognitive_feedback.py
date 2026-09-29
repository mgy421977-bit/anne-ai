from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.learning.critic_loop import LoopDecision
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


class _FakeOrchestrator:
    def __init__(self, result: OrchestrationResult) -> None:
        self.result = result

    def run(self, *args, **kwargs) -> OrchestrationResult:
        return self.result


class _ProceedCritic:
    def decide(self, *args, **kwargs) -> LoopDecision:
        return LoopDecision(
            action="PROCEED",
            reason="test bounded loop permits continuation",
            research_allowed=True,
        )


def _decision_loop_for_state(
    *,
    verification_status: str | None,
    verification_sources: tuple[str, ...] = (),
    requires_evidence: bool | None = None,
    intent: str | None = None,
) -> DecisionLoop:
    fail_fast = FailFastResult(True, "ok")
    state = SimpleNamespace(
        output={"verdict": "ONAYLA", "action": "PROCEED", "reason": "test decision"},
        action="PROCEED",
        context_map={
            "verification_status": verification_status,
            "verification_sources": verification_sources,
            **(
                {"requires_evidence": requires_evidence}
                if requires_evidence is not None
                else {}
            ),
            **({"intent": intent} if intent is not None else {}),
        },
        ethic_score=None,
    )
    orchestration = OrchestrationResult(
        status="EXECUTED",
        fail_fast=fail_fast,
        state=state,
        selection=None,
        stage_trace=("FAIL_FAST", "DUY", "SELECT", "ANLA", "YAP"),
        reason="test decision",
        retry_count=0,
        lineage=("or_runtime_test",),
        stop_reason="validated",
    )
    loop = DecisionLoop.__new__(DecisionLoop)
    loop.orchestrator = _FakeOrchestrator(orchestration)
    loop.research_loop = ResearchCognitiveLoop(critic_loop=_ProceedCritic())
    return loop


def test_runtime_routes_verified_trace_with_missing_intent_to_review() -> None:
    loop = _decision_loop_for_state(
        verification_status="VERIFIED",
        verification_sources=("source-a",),
    )

    result = loop.run("Question")

    assert result.status == "BOUNDED"
    assert result.verdict == "REVIEW"
    assert result.action == "REVIEW"
    assert result.research_state is not None
    assert result.research_state.adaptive_learning is not None
    assert (
        result.research_state.adaptive_learning.metacognition.requires_review is True
    )
    assert result.trace is not None
    assert result.trace.learning["metacognition"]["requires_review"] is True


def test_runtime_routes_unverified_trace_to_bounded_research() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")

    assert result.status == "BOUNDED"
    assert result.verdict == "RESEARCH"
    assert result.action == "RESEARCH"
    assert result.research_state is not None
    assert result.research_state.decision.action == "RESEARCH"
    assert result.output["research_questions"]
    assert result.trace is not None
    assert result.trace.learning["metacognition"]["research_required"] is True


def test_runtime_metacognition_never_grants_execution_authority() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")

    assert result.output["action"] == "RESEARCH"
    assert result.output["metacognitive_next_step"] == "RESEARCH"
    assert result.output["original_output"]["action"] == "PROCEED"


def test_runtime_serializes_bounded_research_guidance() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")
    payload = result.as_dict()

    assert payload["research"]["action"] == "RESEARCH"
    assert payload["research"]["research_allowed"] is True
    assert payload["research"]["questions"]

def test_runtime_does_not_research_when_evidence_is_not_required() -> None:
    loop = _decision_loop_for_state(
        verification_status=None,
        requires_evidence=False,
        intent="explore",
    )

    result = loop.run("Exploratory question")

    assert result.status == "EXECUTED"
    assert result.verdict == "ONAYLA"
    assert result.action == "PROCEED"
    assert result.research_state is not None
    assert result.research_state.decision.action == "PROCEED"
    assessment = result.research_state.adaptive_learning.metacognition
    assert "verification is not required by the recorded intent" in assessment.known
    assert assessment.research_required is False
    assert assessment.requires_review is False
