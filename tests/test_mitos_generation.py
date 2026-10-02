"""Tests for the bounded MITOS generation hook."""

from __future__ import annotations

from anne.core.mitos_learning import LearningGuidance
from anne.core.mitos_generation import plan_generation_modes


def test_generation_plan_changes_order_from_verified_guidance() -> None:
    guidance = LearningGuidance(
        context_key="energy:roof",
        preferred_modes=("COMBINE",),
    )

    plan = plan_generation_modes(
        ("EXPLORE", "COMBINE", "INVERT"),
        guidance=guidance,
    )

    assert plan.modes == ("COMBINE", "EXPLORE", "INVERT")
    assert plan.learned is True
    assert plan.context_key == "energy:roof"


def test_generation_plan_demotes_failed_mode() -> None:
    guidance = LearningGuidance(
        context_key="energy:roof",
        avoid_modes=("INVERT",),
    )

    plan = plan_generation_modes(
        ("INVERT", "EXPLORE", "COMBINE"),
        guidance=guidance,
    )

    assert plan.modes == ("EXPLORE", "COMBINE", "INVERT")
    assert plan.learned is True


def test_generation_without_guidance_is_baseline() -> None:
    plan = plan_generation_modes(("EXPLORE", "COMBINE"))

    assert plan.modes == ("EXPLORE", "COMBINE")
    assert plan.learned is False
    assert plan.context_key == ""


def test_generation_plan_does_not_execute_or_authorize() -> None:
    plan = plan_generation_modes(("EXPLORE",))

    assert not hasattr(plan, "execute")
    assert not hasattr(plan, "authorize")
