"""Tests for bounded MITOS learning guidance."""

from __future__ import annotations

from anne.core.mitos_experience import ExperienceStatus, MitosExperience
from anne.core.mitos_feedback import apply_feedback
from anne.core.mitos_learning import derive_learning_guidance


def experience(
    *,
    context_key: str,
    generation_mode: str,
    status: ExperienceStatus,
) -> MitosExperience:
    item = MitosExperience(
        hypothesis=f"hypothesis-{generation_mode}",
        prediction=f"prediction-{generation_mode}",
        predicted_probability=0.4,
        confidence=0.3,
        novelty=0.8,
        testability=0.9,
        expected_benefit=0.7,
        harm_risk=0.0,
        test_cost=0.1,
        status=ExperienceStatus.PREDICTION,
        context_key=context_key,
        generation_mode=generation_mode,
    )
    apply_feedback(
        item,
        observation="observed",
        outcome="outcome",
        status=status,
        prediction_error=0.1,
    )
    return item


def test_verified_experience_prepares_a_measurable_generation_change() -> None:
    item = experience(
        context_key="energy:roof",
        generation_mode="COMBINE",
        status=ExperienceStatus.VERIFIED,
    )

    guidance = derive_learning_guidance([item], context_key="energy:roof")

    assert guidance.preferred_modes == ("COMBINE",)
    assert guidance.rank_modes(("EXPLORE", "COMBINE")) == ("COMBINE", "EXPLORE")


def test_failed_experience_demotes_the_same_generation_mode() -> None:
    item = experience(
        context_key="energy:roof",
        generation_mode="INVERT",
        status=ExperienceStatus.FAILED,
    )

    guidance = derive_learning_guidance([item], context_key="energy:roof")

    assert guidance.avoid_modes == ("INVERT",)
    assert guidance.rank_modes(("INVERT", "EXPLORE")) == ("EXPLORE", "INVERT")


def test_cross_context_experience_is_not_reused() -> None:
    item = experience(
        context_key="energy:ground",
        generation_mode="SIMULATE",
        status=ExperienceStatus.VERIFIED,
    )

    guidance = derive_learning_guidance([item], context_key="energy:roof")

    assert guidance.sample_size == 0
    assert guidance.preferred_modes == ()
    assert guidance.rank_modes(("SIMULATE", "EXPLORE")) == ("SIMULATE", "EXPLORE")


def test_inconclusive_experience_does_not_create_preference_or_avoidance() -> None:
    item = experience(
        context_key="energy:roof",
        generation_mode="EXPLORE",
        status=ExperienceStatus.INCONCLUSIVE,
    )

    guidance = derive_learning_guidance([item], context_key="energy:roof")

    assert guidance.sample_size == 1
    assert guidance.preferred_modes == ()
    assert guidance.avoid_modes == ()


def test_learning_guidance_has_no_execution_authority() -> None:
    item = experience(
        context_key="energy:roof",
        generation_mode="COMBINE",
        status=ExperienceStatus.VERIFIED,
    )

    guidance = derive_learning_guidance([item], context_key="energy:roof")

    assert not hasattr(guidance, "execute")
    assert not hasattr(guidance, "authorize")
