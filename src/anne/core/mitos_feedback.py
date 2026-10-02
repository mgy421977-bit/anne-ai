"""Bounded prediction-to-outcome feedback for MITOS experiences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anne.core.mitos_experience import ExperienceStatus, MitosExperience


@dataclass(frozen=True)
class FeedbackResult:
    """Observed result of closing one MITOS prediction loop."""

    experience_id: str
    status: ExperienceStatus
    prediction_error: float


def apply_feedback(
    experience: MitosExperience,
    *,
    observation: Any,
    outcome: Any,
    status: ExperienceStatus,
    prediction_error: float,
) -> FeedbackResult:
    """Record observation and outcome without changing generation policy."""

    if status not in {
        ExperienceStatus.VERIFIED,
        ExperienceStatus.FAILED,
        ExperienceStatus.INCONCLUSIVE,
    }:
        raise ValueError("feedback requires a completed experience status")

    experience.record_observation(observation)
    experience.complete(outcome, status, prediction_error)
    experience.validate()

    return FeedbackResult(
        experience_id=experience.experience_id,
        status=experience.status,
        prediction_error=experience.prediction_error or 0.0,
    )
