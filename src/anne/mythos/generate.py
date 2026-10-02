"""MITOS generation boundary for Phase 1a."""
from __future__ import annotations

from anne.core.mitos_generation import MitosGenerationPlan
from anne.mythos.candidate import HypothesisCandidate
from anne.mythos.engine import ExplorationMode, MitosEngine


def generate_candidates(
    goal: str,
    *,
    batch_size: int = 6,
    engine: MitosEngine | None = None,
    generation_plan: MitosGenerationPlan | None = None,
) -> list[HypothesisCandidate]:
    """Generate proposals only, optionally following bounded mode guidance.

    The generation plan changes candidate-generation order only. It does not
    select, evaluate, authorize, or execute a candidate.
    """
    selected_engine = engine or MitosEngine()
    mode_order: tuple[ExplorationMode, ...] | None = None

    if generation_plan is not None:
        valid_modes = {mode.value: mode for mode in ExplorationMode}
        guided = tuple(
            valid_modes[mode]
            for mode in generation_plan.modes
            if mode in valid_modes
        )
        if guided:
            remaining = tuple(mode for mode in ExplorationMode if mode not in guided)
            mode_order = guided + remaining

    if mode_order is None:
        return selected_engine.generate(goal, batch_size=batch_size)

    return selected_engine.generate(
        goal,
        batch_size=batch_size,
        mode_order=mode_order,
    )


__all__ = ["generate_candidates"]
