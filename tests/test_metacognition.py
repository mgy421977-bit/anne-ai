"""Tests for bounded ANNE metacognitive assessment."""

from anne.core.cognitive_state import CognitiveState, Hypothesis
from anne.learning.evidence import EvidenceItem, SupportStatus
from anne.learning.metacognition import MetacognitiveEvaluator


def _evidence(support: str) -> EvidenceItem:
    return EvidenceItem(
        source=f"source-{support}",
        claim="test claim",
        kind="web",
        provenance=f"https://example.test/{support}",
        confidence=0.8,
        passage="test passage",
        support=support,
    )


def test_metacognition_preserves_alternatives_and_does_not_override_action():
    state = CognitiveState(
        raw_input="question",
        intent="question",
        intent_confidence=0.95,
        requires_evidence=True,
        evidence_status="verified",
        action="PROCEED",
        ambiguity=0.1,
    )
    selected = Hypothesis("h1", "topic", "selected claim", 0.9)
    alternative = Hypothesis("h2", "topic", "alternative claim", 0.2)

    assessment = MetacognitiveEvaluator().assess(
        state,
        selected,
        [selected, alternative],
        [_evidence(SupportStatus.SUPPORTS.value)],
    )

    assert assessment.action == "PROCEED"
    assert assessment.alternatives == ("alternative claim",)
    assert assessment.further_research_required is False


def test_metacognition_marks_conflict_and_research_need():
    state = CognitiveState(
        raw_input="question",
        intent="question",
        intent_confidence=0.95,
        requires_evidence=True,
        evidence_status="conflicting",
        action="ABSTAIN",
        ambiguity=0.2,
    )

    assessment = MetacognitiveEvaluator().assess(
        state,
        evidence=[
            _evidence(SupportStatus.SUPPORTS.value),
            _evidence(SupportStatus.CONTRADICTS.value),
        ],
    )

    assert assessment.supporting_evidence == 1
    assert assessment.contradicting_evidence == 1
    assert assessment.contradiction_detected is True
    assert assessment.uncertainty >= 0.8
    assert assessment.further_research_required is True


def test_metacognition_never_upgrades_unclear_evidence():
    state = CognitiveState(
        raw_input="question",
        intent="question",
        intent_confidence=0.95,
        requires_evidence=True,
        evidence_status="unverified",
        action="ABSTAIN",
        ambiguity=0.1,
    )

    assessment = MetacognitiveEvaluator().assess(
        state,
        evidence=[_evidence(SupportStatus.UNCLEAR.value)],
    )

    assert assessment.epistemic_status == "unverified"
    assert assessment.unclear_evidence == 1
    assert assessment.further_research_required is True
    assert assessment.uncertainty >= 0.7


def test_metacognition_requires_no_external_provider():
    state = CognitiveState(
        raw_input="hello",
        intent="greeting",
        intent_confidence=1.0,
        requires_evidence=False,
        evidence_status="not_required",
        action="PROCEED",
        ambiguity=0.0,
    )

    assessment = MetacognitiveEvaluator().assess(state)

    assert assessment.action == "PROCEED"
    assert assessment.evidence_count == 0
    assert assessment.further_research_required is False
