"""Bounded MITOS hypothesis and experience contracts.

This module turns the documented MITOS lifecycle into a small, testable
record without granting hypotheses, predictions, or outcomes execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ExperienceStatus(StrEnum):
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTION = "PREDICTION"
    TESTED = "TESTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class MitosExperience:
    """One reconstructable MITOS hypothesis-to-outcome experience."""

    hypothesis: str
    prediction: str
    predicted_probability: float
    confidence: float
    novelty: float
    testability: float
    expected_benefit: float
    harm_risk: float
    test_cost: float
    experience_id: str = field(default_factory=lambda: f"M-{uuid4().hex[:12]}")
    status: ExperienceStatus = ExperienceStatus.HYPOTHESIS
    observation: Any | None = None
    outcome: Any | None = None
    prediction_error: float | None = None
    provenance: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.experience_id.strip():
            raise ValueError("experience_id is required")
        if not self.hypothesis.strip() or not self.prediction.strip():
            raise ValueError("hypothesis and prediction are required")

        for name, value in (
            ("predicted_probability", self.predicted_probability),
            ("confidence", self.confidence),
            ("novelty", self.novelty),
            ("testability", self.testability),
            ("expected_benefit", self.expected_benefit),
            ("harm_risk", self.harm_risk),
            ("test_cost", self.test_cost),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

        if self.prediction_error is not None and self.prediction_error < 0:
            raise ValueError("prediction_error cannot be negative")

        if self.status in {
            ExperienceStatus.TESTED,
            ExperienceStatus.VERIFIED,
            ExperienceStatus.FAILED,
            ExperienceStatus.INCONCLUSIVE,
        } and self.observation is None:
            raise ValueError("tested experiences require an observation")

        if self.status in {
            ExperienceStatus.VERIFIED,
            ExperienceStatus.FAILED,
            ExperienceStatus.INCONCLUSIVE,
        } and self.outcome is None:
            raise ValueError("completed experiences require an outcome")

    def record_observation(self, observation: Any) -> None:
        if self.status not in {
            ExperienceStatus.PREDICTION,
            ExperienceStatus.TESTED,
        }:
            raise ValueError("observation requires PREDICTION or TESTED status")
        self.observation = observation
        self.status = ExperienceStatus.TESTED

    def complete(self, outcome: Any, status: ExperienceStatus, prediction_error: float) -> None:
        if status not in {
            ExperienceStatus.VERIFIED,
            ExperienceStatus.FAILED,
            ExperienceStatus.INCONCLUSIVE,
        }:
            raise ValueError("completion status must be VERIFIED, FAILED, or INCONCLUSIVE")
        if prediction_error < 0:
            raise ValueError("prediction_error cannot be negative")
        if self.observation is None:
            raise ValueError("an observation is required before completion")

        self.outcome = outcome
        self.prediction_error = prediction_error
        self.status = status
