import pytest

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
    assert "verification is not required by the recorded intent" not in result.known
    assert result.research_required is False
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


def test_metacognition_does_not_research_when_evidence_is_not_required() -> None:
    trace = CycleTrace(
        cycle_id="m9",
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


def test_metacognition_does_not_learn_missing_intent_as_not_required() -> None:
    trace = CycleTrace(
        cycle_id="m10",
        status="SUCCESS",
        decision={"reason": "intent was omitted"},
    )
    result = Metacognition().assess(trace)
    assert "verification is not required by the recorded intent" not in result.known
    assert "factual status is not established as VERIFIED" in result.unknown
    assert result.research_required is False
    assert result.requires_review is True


@pytest.mark.parametrize(
    ("name", "intent", "verification", "reason", "expected_status", "expected_research"),
    [
        (
            "not_required",
            {"intent": "explore", "requires_evidence": False},
            {},
            "exploratory response",
            "PROCESS_COMPLETE",
            False,
        ),
        (
            "unverified",
            {"intent": "answer", "requires_evidence": True},
            {"verification_status": "UNVERIFIED"},
            "evidence pending",
            "PROCESS_REVIEW_REQUIRED",
            True,
        ),
        (
            "conflicting",
            {"intent": "answer", "requires_evidence": True},
            {"verification_status": "CONFLICTING"},
            "sources conflict",
            "PROCESS_REVIEW_REQUIRED",
            True,
        ),
        (
            "refuted",
            {"intent": "answer", "requires_evidence": True},
            {"verification_status": "REFUTED", "verification_sources": ("source-a",)},
            "claim disproved",
            "PROCESS_REVIEW_REQUIRED",
            False,
        ),
        (
            "verified_with_provenance",
            {"intent": "answer", "requires_evidence": True},
            {"verification_status": "VERIFIED", "verification_sources": ("source-a",)},
            "claim supported",
            "PROCESS_COMPLETE",
            False,
        ),
        (
            "verified_without_provenance",
            {"intent": "answer", "requires_evidence": True},
            {"verification_status": "VERIFIED"},
            "claim supported",
            "PROCESS_REVIEW_REQUIRED",
            False,
        ),
        (
            "missing_intent",
            {},
            {},
            "intent omitted",
            "PROCESS_REVIEW_REQUIRED",
            False,
        ),
    ],
)
def test_metacognition_contract_matrix(
    name: str,
    intent: dict,
    verification: dict,
    reason: str,
    expected_status: str,
    expected_research: bool,
) -> None:
    trace = CycleTrace(
        cycle_id=f"matrix-{name}",
        status="SUCCESS",
        intent=intent,
        verification=verification,
        decision={"reason": reason},
    )

    result = Metacognition().assess(trace)

    assert result.evaluation_status == expected_status
    assert result.research_required is expected_research
