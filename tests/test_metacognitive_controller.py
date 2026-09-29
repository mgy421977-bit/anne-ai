from anne.learning.critic_loop import LoopDecision
from anne.learning.metacognitive import MetacognitiveAssessment
from anne.learning.metacognitive_controller import MetacognitiveController


def _assessment(
    *,
    status: str,
    research_required: bool,
    reason: str = "",
) -> MetacognitiveAssessment:
    return MetacognitiveAssessment(
        known=(),
        unknown=(),
        evidence_basis=(),
        assumptions=(),
        decision_dependencies=(),
        recalibration_triggers=(),
        evaluation_status=status,
        research_required=research_required,
        research_reason=reason,
    )


def test_controller_routes_review_gap_to_review_without_research() -> None:
    assessment = _assessment(
        status="PROCESS_REVIEW_REQUIRED",
        research_required=False,
        reason="intent_is_missing",
    )
    decision = LoopDecision("PROCEED", "normal completion", False)

    result = MetacognitiveController().apply(assessment, decision)

    assert result.action == "REVIEW"
    assert result.research_allowed is False


def test_controller_routes_research_signal_only_when_budget_allows() -> None:
    assessment = _assessment(
        status="PROCESS_REVIEW_REQUIRED",
        research_required=True,
        reason="verification_status_does_not_close_the_evidence_loop",
    )
    decision = LoopDecision("RESEARCH", "unresolved evidence", True)

    result = MetacognitiveController().apply(assessment, decision)

    assert result.action == "RESEARCH"
    assert result.research_allowed is True


def test_controller_does_not_override_exhausted_research_budget() -> None:
    assessment = _assessment(
        status="PROCESS_REVIEW_REQUIRED",
        research_required=True,
        reason="verification_status_does_not_close_the_evidence_loop",
    )
    decision = LoopDecision("STOP", "Query budget exhausted", False)

    result = MetacognitiveController().apply(assessment, decision)

    assert result.action == "STOP"
    assert result.research_allowed is False


def test_controller_does_not_grant_execution_authority() -> None:
    assessment = _assessment(
        status="PROCESS_COMPLETE",
        research_required=False,
    )
    decision = LoopDecision("PROCEED", "normal completion", False)

    result = MetacognitiveController().apply(assessment, decision)

    assert result == decision
