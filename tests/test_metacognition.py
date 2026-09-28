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


def test_metacognition_exposes_missing_intent_as_assumption() -> None:
    trace = CycleTrace(cycle_id="m3", status="BOUNDED")
    result = Metacognition().assess(trace)
    assert "intent is not explicitly recorded" in result.assumptions
    assert "intent_clarification" in result.recalibration_triggers
