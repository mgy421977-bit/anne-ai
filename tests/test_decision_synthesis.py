from anne.learning.hypothesis import (
    CriticResult,
    HypothesisAssessment,
    HypothesisStatus,
)
from anne.learning.decision_synthesis import DecisionSynthesizer, SynthesisStatus


def _critic(*assessments: HypothesisAssessment) -> CriticResult:
    return CriticResult(
        assessments=tuple(assessments),
        needs_more_research=True,
        unresolved_hypotheses=tuple(
            a.hypothesis_id
            for a in assessments
            if a.status == HypothesisStatus.UNRESOLVED
        ),
    )


def _a(hypothesis_id: str, status: HypothesisStatus, support=0, contradiction=0):
    return HypothesisAssessment(
        hypothesis_id=hypothesis_id,
        supporting_evidence=support,
        contradicting_evidence=contradiction,
        unresolved_evidence=0,
        status=status,
        reason="test",
    )


def test_single_supported_hypothesis_is_supported() -> None:
    result = DecisionSynthesizer().synthesize(
        _critic(_a("H1", HypothesisStatus.SUPPORTED, support=2))
    )
    assert result.status == SynthesisStatus.SUPPORTED
    assert result.supported_hypotheses == ("H1",)


def test_multiple_supported_hypotheses_are_preserved() -> None:
    result = DecisionSynthesizer().synthesize(
        _critic(
            _a("H1", HypothesisStatus.SUPPORTED, support=2),
            _a("H2", HypothesisStatus.SUPPORTED, support=1),
        )
    )
    assert result.status == SynthesisStatus.MULTIPLE_SUPPORTED
    assert result.supported_hypotheses == ("H1", "H2")


def test_conflict_is_not_collapsed_into_supported() -> None:
    result = DecisionSynthesizer().synthesize(
        _critic(
            _a("H1", HypothesisStatus.UNRESOLVED, support=1, contradiction=1)
        )
    )
    assert result.status == SynthesisStatus.CONFLICTING
    assert result.is_ambiguous is True


def test_rejected_hypothesis_keeps_unresolved_alternative() -> None:
    result = DecisionSynthesizer().synthesize(
        _critic(
            _a("H1", HypothesisStatus.REJECTED, contradiction=2),
            _a("H2", HypothesisStatus.UNRESOLVED),
        )
    )
    assert result.status == SynthesisStatus.REJECTED_WITH_ALTERNATIVES
    assert result.rejected_hypotheses == ("H1",)
    assert result.unresolved_hypotheses == ("H2",)


def test_no_decisive_support_is_insufficient() -> None:
    result = DecisionSynthesizer().synthesize(
        _critic(
            _a("H1", HypothesisStatus.UNRESOLVED),
            _a("H2", HypothesisStatus.UNRESOLVED),
        )
    )
    assert result.status == SynthesisStatus.INSUFFICIENT_EVIDENCE
