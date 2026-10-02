"""Tests for bounded MITOS learning guidance on the real generator."""
from __future__ import annotations

from anne.core.mitos_generation import MitosGenerationPlan
from anne.mythos.engine import ExplorationMode, MitosEngine
from anne.mythos.generate import generate_candidates


def test_generation_plan_changes_real_generator_mode_order() -> None:
    plan = MitosGenerationPlan(
        context_key="ctx-1",
        modes=("association", "hypothesis", "curiosity"),
        learned=True,
    )

    candidates = generate_candidates(
        "bounded discovery task",
        batch_size=3,
        engine=MitosEngine(seed=7),
        generation_plan=plan,
    )

    assert [candidate.mode for candidate in candidates] == [
        ExplorationMode.ASSOCIATION,
        ExplorationMode.HYPOTHESIS,
        ExplorationMode.CURIOSITY,
    ]


def test_generation_without_guidance_preserves_existing_order() -> None:
    candidates = generate_candidates(
        "bounded discovery task",
        batch_size=3,
        engine=MitosEngine(seed=7),
    )

    assert [candidate.mode for candidate in candidates] == [
        ExplorationMode.HYPOTHESIS,
        ExplorationMode.CURIOSITY,
        ExplorationMode.ASSOCIATION,
    ]


def test_generation_plan_does_not_change_candidate_evaluation_fields() -> None:
    baseline = generate_candidates(
        "bounded discovery task",
        batch_size=3,
        engine=MitosEngine(seed=7),
    )
    guided = generate_candidates(
        "bounded discovery task",
        batch_size=3,
        engine=MitosEngine(seed=7),
        generation_plan=MitosGenerationPlan(
            context_key="ctx-1",
            modes=("association", "hypothesis", "curiosity"),
            learned=True,
        ),
    )

    assert [candidate.id for candidate in baseline] == [
        candidate.id for candidate in guided
    ]
    assert sorted(candidate.discovery_value for candidate in baseline) == sorted(
        candidate.discovery_value for candidate in guided
    )
    assert all(candidate.harm_risk == 0.0 for candidate in guided)


def test_generation_plan_ignores_unknown_guidance_modes_without_authority() -> None:
    plan = MitosGenerationPlan(
        context_key="ctx-1",
        modes=("unknown-mode", "association"),
        learned=True,
    )

    candidates = generate_candidates(
        "bounded discovery task",
        batch_size=3,
        engine=MitosEngine(seed=7),
        generation_plan=plan,
    )

    assert candidates[0].mode is ExplorationMode.ASSOCIATION
    assert {candidate.mode for candidate in candidates} == set(ExplorationMode)
