from anne.learning.hypothesis import HypothesisEngine, HypothesisStatus, HypothesisCritic


def test_supported_primary_hypothesis_does_not_suppress_alternatives() -> None:
    hypotheses = HypothesisEngine().generate("Question")
    assert [item.id for item in hypotheses] == ["H1", "H2", "H3"]

    result = HypothesisCritic().assess(
        hypotheses,
        [("H1", "SUPPORTS")],
    )

    statuses = {item.hypothesis_id: item.status for item in result.assessments}
    assert statuses["H1"] is HypothesisStatus.SUPPORTED
    assert statuses["H2"] is HypothesisStatus.UNRESOLVED
    assert statuses["H3"] is HypothesisStatus.UNRESOLVED


def test_alternative_hypothesis_is_not_promoted_without_explicit_evidence() -> None:
    hypotheses = HypothesisEngine().generate("Question")
    result = HypothesisCritic().assess(hypotheses, [("H1", "SUPPORTS")])

    h2 = next(item for item in result.assessments if item.hypothesis_id == "H2")
    assert h2.status is not HypothesisStatus.SUPPORTED
