from anne.learning.evidence import EvidenceItem, SupportStatus
from anne.learning.hypothesis import HypothesisEngine, HypothesisStatus
from anne.learning.hypothesis_bridge import EvidenceHypothesisBridge


def _evidence(claim: str, support: str) -> EvidenceItem:
    return EvidenceItem(
        source="test-source",
        claim=claim,
        kind="web",
        provenance="https://example.test/source",
        confidence=0.9,
        passage=claim,
        support=support,
    )


def test_evidence_bridge_maps_support_signal() -> None:
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=1)
    result = EvidenceHypothesisBridge().assess(
        hypotheses,
        [_evidence(hypotheses[0].claim, SupportStatus.SUPPORTS.value)],
    )
    assert result.assessments[0].status is HypothesisStatus.SUPPORTED


def test_evidence_bridge_preserves_conflict() -> None:
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=1)
    result = EvidenceHypothesisBridge().assess(
        hypotheses,
        [
            _evidence(hypotheses[0].claim, SupportStatus.SUPPORTS.value),
            _evidence(hypotheses[0].claim, SupportStatus.CONTRADICTS.value),
        ],
    )
    assert result.assessments[0].status is HypothesisStatus.UNRESOLVED
    assert result.needs_more_research is True


def test_evidence_bridge_ignores_unrelated_claims() -> None:
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=1)
    result = EvidenceHypothesisBridge().assess(
        hypotheses,
        [_evidence("unrelated claim", SupportStatus.SUPPORTS.value)],
    )
    assert result.assessments[0].status is HypothesisStatus.UNRESOLVED
