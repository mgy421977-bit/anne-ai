"""Bounded learning guidance derived from completed MITOS experiences.

Learning guidance is an explicit input to a later generation step. It does
not mutate policy, grant authority, or execute an action.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from anne.core.mitos_experience import ExperienceStatus, MitosExperience


@dataclass(frozen=True)
class LearningGuidance:
    """Context-scoped generation guidance backed by completed experiences."""

    context_key: str
    preferred_modes: tuple[str, ...] = ()
    avoid_modes: tuple[str, ...] = ()
    sample_size: int = 0

    def rank_modes(self, modes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        """Return a stable, bounded ordering for an explicit generation input."""

        preferred = set(self.preferred_modes)
        avoided = set(self.avoid_modes)
        order = {mode: index for index, mode in enumerate(modes)}

        def key(mode: str) -> tuple[int, int]:
            if mode in preferred:
                return (0, order[mode])
            if mode in avoided:
                return (2, order[mode])
            return (1, order[mode])

        return tuple(sorted(modes, key=key))


def derive_learning_guidance(
    experiences: tuple[MitosExperience, ...] | list[MitosExperience],
    *,
    context_key: str,
) -> LearningGuidance:
    """Derive exact-context guidance from completed experience outcomes."""

    if not context_key.strip():
        raise ValueError("context_key is required")

    matched = [
        item
        for item in experiences
        if item.context_key == context_key
        and item.status
        in {
            ExperienceStatus.VERIFIED,
            ExperienceStatus.FAILED,
            ExperienceStatus.INCONCLUSIVE,
        }
        and item.generation_mode.strip()
    ]

    verified = Counter(
        item.generation_mode for item in matched if item.status is ExperienceStatus.VERIFIED
    )
    failed = Counter(
        item.generation_mode for item in matched if item.status is ExperienceStatus.FAILED
    )

    modes = set(verified) | set(failed)
    preferred = tuple(sorted(mode for mode in modes if verified[mode] > failed[mode]))
    avoided = tuple(sorted(mode for mode in modes if failed[mode] > verified[mode]))

    return LearningGuidance(
        context_key=context_key,
        preferred_modes=preferred,
        avoid_modes=avoided,
        sample_size=len(matched),
    )
