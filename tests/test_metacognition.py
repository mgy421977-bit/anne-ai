from anne.core.trace import CycleTrace
from anne.learning.metacognition import Metacognition


def test_metacognition_does_not_treat_confidence_as_truth() -> None:
    trace = CycleTrace(
        cycle_id="m1",
        status="BOUNDED",
        verification={"verification_status": "UNVERIFIED"},
        decision={"reason": "confidence=0.99"},
    )
    result = Metacognition().assess(trace)
    assert "factual status is not established as VERIFIED" in result.unknown
    assert "new_independent_evidence" in result.recalibration_triggers
    assert result.research_required is True
    assert result.requires_review is True


def test_metacognition_records_explicit_verified_basis() -> None:
    trace = CycleTrace(
        cycle_id="m2",
        status="SUCCESS",
        intent={"intent": "answer"},
        hypotheses=({"id": "h1"},),
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a", "source-b"),
        },
        decision={"reason": "independent evidence supports claim"},
    )
    result = Metacognition().assess(trace)
    assert result.known == ("verification status is explicitly VERIFIED",)
    assert result.evidence_basis == ("verification_sources",)
    assert "decision_reason" in result.decision_dependencies
    assert result.evaluation_status == "PROCESS_COMPLETE"
    assert result.research_required is False
    assert result.requires_review is False


def test_metacognition_exposes_missing_intent_as_assumption() -> None:
    trace = CycleTrace(cycle_id="m3", status="BOUNDED")
    result = Metacognition().assess(trace)
    assert "intent is not explicitly recorded" in result.assumptions
    assert "intent_clarification" in result.recalibration_triggers
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"


def test_metacognition_marks_conflicting_evidence_for_research() -> None:
    trace = CycleTrace(
        cycle_id="m4",
        status="BOUNDED",
        intent={"intent": "answer"},
        decision={"reason": "sources conflict"},
        verification={
            "verification_status": "CONFLICTING",
            "verification_sources": ("source-a", "source-b"),
        },
    )
    result = Metacognition().assess(trace)
    assert result.research_required is True
    assert result.requires_review is True
    assert result.research_reason == (
        "verification_status_does_not_close_the_evidence_loop"
    )


def test_metacognition_requires_review_for_verified_without_provenance() -> None:
    trace = CycleTrace(
        cycle_id="m5",
        status="SUCCESS",
        intent={"intent": "answer"},
        decision={"reason": "claim reviewed"},
        verification={"verification_status": "VERIFIED"},
    )
    result = Metacognition().assess(trace)
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert result.requires_review is True
    assert result.research_required is False
    assert result.research_reason == "provenance_is_incomplete"
    assert "provenance_completion" in result.recalibration_triggers


def test_metacognition_requires_review_without_decision_reason() -> None:
    trace = CycleTrace(
        cycle_id="m6",
        status="SUCCESS",
        intent={"intent": "answer"},
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a",),
        },
    )
    result = Metacognition().assess(trace)
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert result.requires_review is True
    assert result.research_required is False


def test_metacognition_requires_review_without_intent() -> None:
    trace = CycleTrace(
        cycle_id="m7",
        status="SUCCESS",
        decision={"reason": "claim reviewed"},
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a",),
        },
    )
    result = Metacognition().assess(trace)
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert result.requires_review is True
    assert result.research_required is False


def test_metacognition_does_not_force_research_for_refuted_claim() -> None:
    trace = CycleTrace(
        cycle_id="m8",
        status="BOUNDED",
        intent={"intent": "answer"},
        decision={"reason": "claim was disproved"},
        verification={
            "verification_status": "REFUTED",
            "verification_sources": ("source-a",),
        },
    )
    result = Metacognition().assess(trace)
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert result.requires_review is True
    assert result.research_required is False
    assert result.research_reason == ""


def test_metacognition_keeps_language_corroboration_non_authoritative():
    trace = CycleTrace(
        cycle_id="m9",
        status="SUCCESS",
        intent={"intent": "answer"},
        decision={"reason": "claim reviewed"},
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a", "source-b"),
        },
        language_corroboration={
            "status": "corroborated",
            "authoritative": False,
            "providers": ["bitigci", "tdk"],
        },
    )
    result = Metacognition().assess(trace)

    assert "language_corroboration_observation" in result.decision_dependencies
    assert result.evaluation_status == "PROCESS_COMPLETE"
    assert result.research_required is False
    assert result.requires_review is False


def test_metacognition_routes_language_divergence_to_review_not_research():
    trace = CycleTrace(
        cycle_id="m10",
        status="SUCCESS",
        intent={"intent": "answer"},
        decision={"reason": "claim reviewed"},
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a", "source-b"),
        },
        language_corroboration={
            "status": "divergent",
            "authoritative": False,
            "providers": ["bitigci", "tdk"],
        },
    )
    result = Metacognition().assess(trace)

    assert "language_source_divergence" in result.recalibration_triggers
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert result.requires_review is True
    assert result.research_required is False
    assert result.research_reason == ""
    assert result.unknown == ()


def test_metacognition_controller_routes_language_divergence_to_review():
    from anne.learning.critic_loop import LoopDecision
    from anne.learning.metacognitive_controller import MetacognitiveController

    trace = CycleTrace(
        cycle_id="runtime-language-divergence",
        status="SUCCESS",
        intent={"intent": "answer"},
        decision={"reason": "claim reviewed"},
        verification={
            "verification_status": "VERIFIED",
            "verification_sources": ("source-a", "source-b"),
        },
        language_corroboration={
            "status": "divergent",
            "authoritative": False,
            "providers": ["bitigci", "tdk"],
        },
    )
    assessment = Metacognition().assess(trace)
    decision = MetacognitiveController().apply(
        assessment,
        LoopDecision(
            action="PROCEED",
            reason="continue",
            research_allowed=True,
        ),
    )

    assert decision.action == "REVIEW"
    assert decision.research_allowed is False


def test_metacognition_does_not_research_when_evidence_is_not_required() -> None:
    trace = CycleTrace(
        cycle_id="m11",
        status="SUCCESS",
        intent={"intent": "explore", "requires_evidence": False},
        decision={"reason": "non-factual exploratory response"},
    )
    result = Metacognition().assess(trace)
    assert result.known == (
        "verification is not required by the recorded intent",
    )
    assert result.evaluation_status == "PROCESS_COMPLETE"
    assert result.research_required is False
    assert result.requires_review is False


def test_metacognition_missing_intent_is_not_treated_as_not_required() -> None:
    trace = CycleTrace(
        cycle_id="m12",
        status="SUCCESS",
        decision={"reason": "intent omitted"},
    )
    result = Metacognition().assess(trace)
    assert "verification is not required by the recorded intent" not in result.known
    assert "factual status is not established as VERIFIED" in result.unknown
    assert result.evaluation_status == "PROCESS_REVIEW_REQUIRED"
