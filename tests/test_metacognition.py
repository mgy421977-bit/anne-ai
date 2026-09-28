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
    assert "factual status is not established as VERIFIED with recorded provenance" in result.unknown
    assert "new_independent_evidence" in result.recalibration_triggers


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
    assert result.known == ("verification status is explicitly VERIFIED with recorded sources",)
    assert result.evidence_basis == ("verification_sources",)
    assert "decision_reason" in result.decision_dependencies


def test_metacognition_exposes_missing_intent_as_assumption() -> None:
    trace = CycleTrace(cycle_id="m3", status="BOUNDED")
    result = Metacognition().assess(trace)
    assert "intent is not explicitly recorded" in result.assumptions
    assert "intent_clarification" in result.recalibration_triggers


def test_metacognition_does_not_call_verified_without_provenance() -> None:
    trace = CycleTrace(
        cycle_id="m4",
        status="SUCCESS",
        verification={"verification_status": "VERIFIED"},
    )
    result = Metacognition().assess(trace)
    assert not result.known
    assert "provenance_completion" in result.recalibration_triggers


def test_metacognition_distinguishes_conflicting_and_refuted_evidence() -> None:
    conflicting = CycleTrace(
        cycle_id="m5",
        status="BOUNDED",
        verification={"verification_status": "CONFLICTING", "verification_sources": ("a", "b")},
    )
    refuted = CycleTrace(
        cycle_id="m6",
        status="BOUNDED",
        verification={"verification_status": "REFUTED", "verification_sources": ("a",)},
    )

    conflicting_result = Metacognition().assess(conflicting)
    refuted_result = Metacognition().assess(refuted)

    assert "resolve_conflicting_evidence" in conflicting_result.recalibration_triggers
    assert "reassess_refuted_claim" in refuted_result.recalibration_triggers


def test_metacognition_marks_review_decisions_for_reassessment() -> None:
    trace = CycleTrace(
        cycle_id="m7",
        status="BOUNDED",
        decision={"verdict": "REVIEW", "reason": "human review required"},
    )
    result = Metacognition().assess(trace)
    assert "decision_status" in result.decision_dependencies
    assert "decision_reassessment" in result.recalibration_triggers
