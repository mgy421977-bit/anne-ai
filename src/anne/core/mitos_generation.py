"""Bounded MITOS generation hook for explicit learning guidance."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.mitos_learning import LearningGuidance


@dataclass(frozen=True)
class MitosGenerationPlan:
    """Deterministic generation-mode plan; it does not execute generation."""

    context_key: str
    modes: tuple[str, ...]
    learned: bool


def plan_generation_modes(
    modes: tuple[str, ...] | list[str],
    *,
    guidance: LearningGuidance | None = None,
) -> MitosGenerationPlan:
    """Apply optional bounded guidance to an explicit MITOS mode list."""

    normalized = tuple(dict.fromkeys(mode.strip() for mode in modes if mode.strip()))
    if not normalized:
        raise ValueError("at least one generation mode is required")

    if guidance is None:
        return MitosGenerationPlan("", normalized, False)

    ranked = guidance.rank_modes(normalized)
    return MitosGenerationPlan(guidance.context_key, ranked, ranked != normalized)
