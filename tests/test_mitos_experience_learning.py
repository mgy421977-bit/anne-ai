"""Regression tests for the bounded MITOS -> ANNE experience bridge."""

from anne.learning.mitos_experience import MitosExperienceAdapter
from anne.mythos.experience import ExperienceRecord, ExperienceStatus


def test_hypothesis_and_prediction_are_not_learning_evidence() -> None:
    adapter = MitosExperienceAdapter()
    hypothesis = ExperienceRecord("h1", "goal", "claim")
    prediction = ExperienceRecord(
        "h2",
        "goal",
        "claim",
        status=ExperienceStatus.PREDICTION,
    )

    assert adapter.to_experience(hypothesis) is None
    assert adapter.to_experience(prediction) is None


def test_verified_mitos_outcome_becomes_non_authoritative_success() -> None:
    record = ExperienceRecord(
        "h3",
        "goal",
        "claim",
        status=ExperienceStatus.VERIFIED,
        context={"mode": "hypothesis", "testability": 0.9},
    )
    adapter = MitosExperienceAdapter()

    experience = adapter.to_experience(
        record,
        strategy="bounded_test",
    )

    assert experience is not None
    assert experience.outcome == "SUCCESS"
    assert experience.factual_status == "VERIFIED"
    assert experience.safe_to_reuse is False
    assert experience.strategy == "bounded_test"
    assert experience.context_key == "mitos"


def test_failed_mitos_outcome_preserves_explicit_failure_class_only() -> None:
    record = ExperienceRecord(
        "h4",
        "goal",
        "claim",
        status=ExperienceStatus.FAILED,
        context={"mode": "curiosity"},
    )
    adapter = MitosExperienceAdapter()

    experience = adapter.to_experience(
        record,
        strategy="bounded_test",
        failure_class="evidence_gap",
    )

    assert experience is not None
    assert experience.outcome == "FAILURE"
    assert experience.failure_class == "evidence_gap"
    assert experience.factual_status == "UNVERIFIED"
    assert experience.safe_to_reuse is False


def test_inconclusive_mitos_outcome_does_not_become_verified_truth() -> None:
    record = ExperienceRecord(
        "h5",
        "goal",
        "claim",
        status=ExperienceStatus.INCONCLUSIVE,
    )

    experience = MitosExperienceAdapter().to_experience(record)

    assert experience is not None
    assert experience.outcome == "FAILURE"
    assert experience.factual_status == "UNVERIFIED"
    assert experience.safe_to_reuse is False
    assert experience.failure_class == "unknown"
