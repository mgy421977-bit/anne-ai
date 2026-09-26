from __future__ import annotations

from anne.learning.hypothesis import (
    HypothesisCritic,
    HypothesisEngine,
    HypothesisStatus,
)


def test_hypothesis_engine_creates_bounded_alternatives() -> None:
    engine = HypothesisEngine()
    hypotheses = engine.generate("What explains the observed result?")
    assert len(hypotheses) == 3
    assert hypotheses[0].id == "H1"
    assert hypotheses[1].id == "H2"
    assert hypotheses[2].id == "H3"


def test_hypothesis_engine_respects_bound() -> None:
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=2)
    assert len(hypotheses) == 2


def test_hypothesis_engine_rejects_empty_question() -> None:
    try:
        HypothesisEngine().generate(" ")
    except ValueError:
        return
    raise AssertionError("empty question must fail closed")


def test_critic_marks_supported_hypothesis() -> None:
    result = HypothesisCritic().assess(
        HypothesisEngine().generate("Question", max_hypotheses=1),
        [("H1", "SUPPORTS")],
    )
    assert result.assessments[0].status is HypothesisStatus.SUPPORTED
    assert result.needs_more_research is False


def test_critic_marks_rejected_hypothesis() -> None:
    result = HypothesisCritic().assess(
        HypothesisEngine().generate("Question", max_hypotheses=1),
        [("H1", "CONTRADICTS")],
    )
    assert result.assessments[0].status is HypothesisStatus.REJECTED


def test_critic_preserves_conflict_and_requests_more_research() -> None:
    result = HypothesisCritic().assess(
        HypothesisEngine().generate("Question", max_hypotheses=1),
        [("H1", "SUPPORTS"), ("H1", "CONTRADICTS")],
    )
    assert result.assessments[0].status is HypothesisStatus.UNRESOLVED
    assert result.needs_more_research is True
    assert result.unresolved_hypotheses == ("H1",)
