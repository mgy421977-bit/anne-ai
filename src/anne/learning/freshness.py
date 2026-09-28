"""Policy-driven freshness assessment for provenance-bearing evidence.

Freshness is temporal metadata, not epistemic truth or authority. The module is
domain-agnostic: callers must supply the reference time and policy thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class FreshnessStatus(StrEnum):
    CURRENT = "current"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FreshnessPolicy:
    """Explicit temporal policy; thresholds are supplied by the caller."""

    aging_after: timedelta
    stale_after: timedelta

    def __post_init__(self) -> None:
        if self.aging_after < timedelta(0):
            raise ValueError("aging_after must not be negative")
        if self.stale_after <= self.aging_after:
            raise ValueError("stale_after must be greater than aging_after")


@dataclass(frozen=True)
class FreshnessAssessment:
    """Non-authoritative assessment of evidence age."""

    status: FreshnessStatus
    retrieved_at: str
    reference_time: str
    age_seconds: float | None
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "retrieved_at": self.retrieved_at,
            "reference_time": self.reference_time,
            "age_seconds": self.age_seconds,
            "reason": self.reason,
        }


class EvidenceFreshness:
    """Assess evidence freshness without changing its factual status."""

    @staticmethod
    def _parse_timestamp(value: str, field_name: str) -> datetime:
        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"{field_name} must include timezone information")
        return parsed.astimezone(UTC)

    @classmethod
    def assess(
        cls,
        retrieved_at: str,
        *,
        reference_time: str,
        policy: FreshnessPolicy,
    ) -> FreshnessAssessment:
        """Classify age against an explicit policy and reference time."""
        retrieved = cls._parse_timestamp(retrieved_at, "retrieved_at")
        reference = cls._parse_timestamp(reference_time, "reference_time")
        age = reference - retrieved

        if age < timedelta(0):
            return FreshnessAssessment(
                FreshnessStatus.UNKNOWN,
                retrieved_at,
                reference_time,
                age.total_seconds(),
                "retrieval time is later than the reference time",
            )

        if age < policy.aging_after:
            status = FreshnessStatus.CURRENT
        elif age < policy.stale_after:
            status = FreshnessStatus.AGING
        else:
            status = FreshnessStatus.STALE

        return FreshnessAssessment(
            status,
            retrieved_at,
            reference_time,
            age.total_seconds(),
            "freshness classified by the caller-supplied temporal policy",
        )


__all__ = [
    "EvidenceFreshness",
    "FreshnessAssessment",
    "FreshnessPolicy",
    "FreshnessStatus",
]
