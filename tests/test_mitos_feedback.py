"""Tests for the bounded MITOS prediction feedback loop."""

from __future__ import annotations

import pytest

from anne.core.mitos_experience import ExperienceStatus, MitosExperience
from anne.core.mitos_feedback import apply_feedback


def experience() -> MitosExperience:
    return MitosExperience(
        hypothesis="A bounded intervention improves the target metric.",
        prediction="The target metric improves.",
        predicted_probability=0.4,
        confidence=0.3,
        novelty=0.8,
        testability=0.9,
        expected_benefit=0.7,
        harm_risk=0.0,
        test_cost=0.1,
        status=ExperienceStatus.PREDICTION,
    )


def test_feedback_keeps_observation_outcome_and_error_distinct() -> None:
    item = experience()

    result = apply_feedback(
        item,
        observation={"metric": 0.2},
        outcome={"metric": 0.1},
        status=ExperienceStatus.FAILED,
        prediction_error=0.3,
    )

    assert result.experience_id == item.experience_id
    assert result.status is ExperienceStatus.FAILED
    assert result.prediction_error == 0.3
    assert item.observation == {"metric": 0.2}
    assert item.outcome == {"metric": 0.1}


def test_feedback_supports_inconclusive_results() -> None:
    item = experience()

    result = apply_feedback(
        item,
        observation="partial observation",
        outcome="insufficient evidence",
        status=ExperienceStatus.INCONCLUSIVE,
        prediction_error=0.2,
    )

    assert result.status is ExperienceStatus.INCONCLUSIVE
    assert item.prediction_error == 0.2


def test_feedback_rejects_non_terminal_status() -> None:
    item = experience()

    with pytest.raises(ValueError, match="completed experience status"):
        apply_feedback(
            item,
            observation="observed",
            outcome="outcome",
            status=ExperienceStatus.TESTED,
            prediction_error=0.1,
        )


def test_feedback_does_not_create_learning_update() -> None:
    item = experience()

    apply_feedback(
        item,
        observation="observed",
        outcome="outcome",
        status=ExperienceStatus.VERIFIED,
        prediction_error=0.0,
    )

    assert not hasattr(item, "learning_update")
