"""Tests for the bounded MITOS experience lifecycle."""

from __future__ import annotations

import pytest

from anne.core.mitos_experience import ExperienceStatus, MitosExperience


def make_experience(**overrides: object) -> MitosExperience:
    values = {
        "hypothesis": "A bounded intervention can improve the target outcome.",
        "prediction": "The target metric will improve.",
        "predicted_probability": 0.4,
        "confidence": 0.3,
        "novelty": 0.8,
        "testability": 0.9,
        "expected_benefit": 0.7,
        "harm_risk": 0.0,
        "test_cost": 0.1,
    }
    values.update(overrides)
    return MitosExperience(**values)


def test_hypothesis_record_validates_and_preserves_lifecycle() -> None:
    experience = make_experience()
    experience.validate()

    assert experience.status is ExperienceStatus.HYPOTHESIS
    assert experience.observation is None
    assert experience.outcome is None


def test_prediction_to_tested_to_failed_records_observation_and_error() -> None:
    experience = make_experience(status=ExperienceStatus.PREDICTION)
    experience.record_observation({"metric": 0.1})
    experience.complete(
        {"metric": 0.0},
        ExperienceStatus.FAILED,
        prediction_error=0.6,
    )

    experience.validate()

    assert experience.status is ExperienceStatus.FAILED
    assert experience.prediction_error == 0.6
    assert experience.observation == {"metric": 0.1}
    assert experience.outcome == {"metric": 0.0}


def test_completed_experience_requires_observation() -> None:
    experience = make_experience(status=ExperienceStatus.FAILED, outcome="no change")

    with pytest.raises(ValueError, match="tested experiences require an observation"):
        experience.validate()


def test_completed_experience_requires_outcome() -> None:
    experience = make_experience(status=ExperienceStatus.VERIFIED, observation="observed")

    with pytest.raises(ValueError, match="completed experiences require an outcome"):
        experience.validate()


@pytest.mark.parametrize(
    "field_name",
    [
        "predicted_probability",
        "confidence",
        "novelty",
        "testability",
        "expected_benefit",
        "harm_risk",
        "test_cost",
    ],
)
def test_scored_fields_are_bounded(field_name: str) -> None:
    experience = make_experience(**{field_name: 1.1})

    with pytest.raises(ValueError, match="must be between 0 and 1"):
        experience.validate()


def test_negative_prediction_error_is_rejected() -> None:
    experience = make_experience(prediction_error=-0.1)

    with pytest.raises(ValueError, match="prediction_error cannot be negative"):
        experience.validate()


def test_completion_cannot_bypass_observation() -> None:
    experience = make_experience(status=ExperienceStatus.PREDICTION)

    with pytest.raises(ValueError, match="an observation is required"):
        experience.complete("outcome", ExperienceStatus.INCONCLUSIVE, 0.2)
