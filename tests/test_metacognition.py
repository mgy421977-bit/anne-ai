from anne.core.cognitive_state import CognitiveState
from anne.learning.metacognition import MetacognitiveReviewer, MetacognitiveAssessment


def _state(**updates) -> CognitiveState:
    state = CognitiveState(
        raw_input="test",
        intent="question",
        requires_evidence=True,
        evidence_status="unverified",
        evidence_verified=False,
        ambiguity=0.4,
        logic_valid=True,
        action="PROCEED",
        context_map={
            "core_decision": "PROCEED",
            "core_reason": "test",
            "agency_gate": "ALLOW",
        },
    )
    state.context_map.update(updates)
    return state


def test_metacognitive_review_requires_research_for_unverified_evidence():
    assessment = MetacognitiveReviewer().review(_state())

    assert isinstance(assessment, MetacognitiveAssessment)
    assert assessment.needs_research is True
    assert assessment.evidence_sufficient is False
    assert assessment.evidence_status == "unverified"


def test_metacognitive_review_detects_conflict_without_collapsing_it():
    state = _state(
        evidence_status="conflicting",
        evidence_verified=False,
        verification_status="CONFLICTING",
        decision_synthesis_status="CONFLICTING",
        decision_synthesis_alternatives=("h1", "h2"),
    )

    assessment = MetacognitiveReviewer().review(state)

    assert assessment.has_conflict is True
    assert assessment.needs_research is True
    assert assessment.alternatives_preserved == ("h1", "h2")


def test_metacognitive_review_records_verified_state_without_granting_authority():
    state = _state(
        evidence_status="verified",
        evidence_verified=True,
        verification_status="VERIFIED",
        agency_gate="ALLOW",
    )

    assessment = MetacognitiveReviewer().review(state)

    assert assessment.evidence_sufficient is True
    assert assessment.needs_research is False
    assert assessment.agency_decision == "ALLOW"


def test_metacognitive_review_flags_refuted_evidence():
    state = _state(
        evidence_status="refuted",
        evidence_verified=False,
        verification_status="REFUTED",
    )

    assessment = MetacognitiveReviewer().review(state)

    assert assessment.needs_research is True
    assert assessment.evidence_sufficient is False
    assert "refuted" in assessment.reason.lower()


def test_metacognitive_review_preserves_low_probability_alternatives():
    state = _state()
    state.low_prob_preserved = [
        {"hypothesis": "alternative", "probability": 0.2, "note": "preserved"}
    ]

    assessment = MetacognitiveReviewer().review(state)

    assert assessment.alternatives_preserved == ("alternative",)
