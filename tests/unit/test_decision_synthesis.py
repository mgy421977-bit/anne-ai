from anne.core.decision_synthesis import (
    DecisionStatus,
    DecisionSynthesizer,
    EvidenceLink,
    EvidenceRelation,
    HypothesisStatus,
    SynthesisHypothesis,
)


def hyp(hid: str) -> SynthesisHypothesis:
    return SynthesisHypothesis(hid, f"claim-{hid}")


def link(eid: str, hid: str, relation: EvidenceRelation, weight: float = 1.0) -> EvidenceLink:
    return EvidenceLink(eid, hid, relation, weight, provenance=f"source:{eid}")


def test_single_supported_hypothesis():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1")],
        evidence=[link("E1", "H1", EvidenceRelation.SUPPORTS)],
    )
    assert result.status is DecisionStatus.SUPPORTED
    assert result.selected_hypothesis == "H1"
    assert result.hypotheses[0].status is HypothesisStatus.SUPPORTED


def test_multiple_supported_hypotheses_are_preserved():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1"), hyp("H2")],
        evidence=[
            link("E1", "H1", EvidenceRelation.SUPPORTS),
            link("E2", "H2", EvidenceRelation.SUPPORTS),
        ],
    )
    assert result.status is DecisionStatus.MULTIPLE_SUPPORTED
    assert result.selected_hypothesis is None
    assert [item.id for item in result.hypotheses] == ["H1", "H2"]


def test_support_plus_contradiction_is_partial():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1")],
        evidence=[
            link("E1", "H1", EvidenceRelation.SUPPORTS),
            link("E2", "H1", EvidenceRelation.CONTRADICTS),
        ],
    )
    assert result.status is DecisionStatus.CONFLICTING
    assert result.hypotheses[0].status is HypothesisStatus.CONTRADICTED


def test_insufficient_evidence_never_becomes_supported():
    result = DecisionSynthesizer().synthesize([hyp("H1")], evidence=[])
    assert result.status is DecisionStatus.INSUFFICIENT_EVIDENCE
    assert result.selected_hypothesis is None
    assert result.hypotheses[0].status is HypothesisStatus.INSUFFICIENT_EVIDENCE


def test_rejected_primary_keeps_alternative():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1"), hyp("H2")],
        evidence=[
            link("E1", "H1", EvidenceRelation.CONTRADICTS, 2.0),
            link("E2", "H2", EvidenceRelation.SUPPORTS),
        ],
    )
    assert result.status is DecisionStatus.SUPPORTED
    assert result.selected_hypothesis == "H2"
    assert result.hypotheses[0].status is HypothesisStatus.REJECTED
    assert result.hypotheses[1].status is HypothesisStatus.SUPPORTED


def test_all_hypotheses_rejected():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1"), hyp("H2")],
        evidence=[
            link("E1", "H1", EvidenceRelation.CONTRADICTS),
            link("E2", "H2", EvidenceRelation.CONTRADICTS),
        ],
    )
    assert result.status is DecisionStatus.REJECTED
    assert result.selected_hypothesis is None


def test_golden_supported_h2_does_not_delete_h1():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1"), hyp("H2"), hyp("H3")],
        evidence=[
            link("E1", "H1", EvidenceRelation.SUPPORTS),
            link("E2", "H2", EvidenceRelation.SUPPORTS),
            link("E3", "H2", EvidenceRelation.SUPPORTS),
        ],
    )
    assert result.status is DecisionStatus.MULTIPLE_SUPPORTED
    assert {item.id for item in result.hypotheses} == {"H1", "H2", "H3"}
    assert next(item for item in result.hypotheses if item.id == "H1").status is HypothesisStatus.SUPPORTED
    assert next(item for item in result.hypotheses if item.id == "H2").status is HypothesisStatus.SUPPORTED
    assert next(item for item in result.hypotheses if item.id == "H3").status is HypothesisStatus.INSUFFICIENT_EVIDENCE


def test_failure_trace_requires_review_action():
    result = DecisionSynthesizer().synthesize(
        [hyp("H1")],
        evidence=[link("E1", "H1", EvidenceRelation.SUPPORTS)],
        failure_trace=[{"id": "F1", "reason": "validation failed"}],
    )
    assert result.failure_trace[0]["id"] == "F1"
    assert "failure traces" in " ".join(result.next_action)
