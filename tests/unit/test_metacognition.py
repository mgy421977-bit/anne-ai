from anne.core.decision_synthesis import (
    DecisionStatus,
    DecisionSynthesis,
    EvidenceLink,
    EvidenceRelation,
    SynthesisHypothesis,
)
from anne.core.metacognition import MetaStatus, MetacognitiveEvaluator


def h(hid: str) -> SynthesisHypothesis:
    return SynthesisHypothesis(hid, f"claim-{hid}")


def e(eid: str, hid: str) -> EvidenceLink:
    return EvidenceLink(eid, hid, EvidenceRelation.SUPPORTS, provenance=f"source:{eid}")


def test_ready_when_single_supported_hypothesis_has_evidence():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.SUPPORTED,
        hypotheses=[h("H1")],
        selected_hypothesis="H1",
        evidence=[e("E1", "H1")],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis, declared_confidence=0.8)
    assert review.status is MetaStatus.READY
    assert review.checks["evidence_available"] is True


def test_multiple_supported_requires_review():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.MULTIPLE_SUPPORTED,
        hypotheses=[h("H1"), h("H2")],
        evidence=[e("E1", "H1"), e("E2", "H2")],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis)
    assert review.status is MetaStatus.REVIEW
    assert "discriminating test" in " ".join(review.next_action)


def test_contradiction_requires_review():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.CONFLICTING,
        hypotheses=[h("H1")],
        evidence=[e("E1", "H1")],
        contradictions=["H1"],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis)
    assert review.status is MetaStatus.REVIEW
    assert review.checks["contradictions_resolved"] is False


def test_insufficient_evidence_abstains():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[h("H1")],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis)
    assert review.status is MetaStatus.ABSTAIN
    assert review.checks["evidence_available"] is False


def test_repeated_failure_changes_strategy():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.SUPPORTED,
        hypotheses=[h("H1")],
        selected_hypothesis="H1",
        evidence=[e("E1", "H1")],
        failure_trace=[
            {"id": "F1", "reason": "verification failed"},
            {"id": "F1", "reason": "verification failed again"},
        ],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis)
    assert review.status is MetaStatus.REVIEW
    assert "Change the reasoning strategy" in " ".join(review.next_action)


def test_confidence_never_overrides_evidence():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[h("H1")],
    )
    review = MetacognitiveEvaluator().evaluate(synthesis, declared_confidence=0.99)
    assert review.status is MetaStatus.ABSTAIN
    assert "requires evidence" in review.confidence_note


def test_confidence_range_is_validated():
    synthesis = DecisionSynthesis(
        status=DecisionStatus.SUPPORTED,
        hypotheses=[h("H1")],
        selected_hypothesis="H1",
        evidence=[e("E1", "H1")],
    )
    try:
        MetacognitiveEvaluator().evaluate(synthesis, declared_confidence=1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range confidence must fail")
