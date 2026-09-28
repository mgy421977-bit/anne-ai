from datetime import timedelta

import pytest

from anne.learning.freshness import (
    EvidenceFreshness,
    FreshnessPolicy,
    FreshnessStatus,
)


def test_current_and_aging_are_policy_driven() -> None:
    policy = FreshnessPolicy(
        aging_after=timedelta(hours=1),
        stale_after=timedelta(hours=24),
    )
    reference = "2026-09-29T12:00:00+00:00"

    current = EvidenceFreshness.assess(
        "2026-09-29T11:30:00+00:00",
        reference_time=reference,
        policy=policy,
    )
    aging = EvidenceFreshness.assess(
        "2026-09-29T10:00:00+00:00",
        reference_time=reference,
        policy=policy,
    )

    assert current.status is FreshnessStatus.CURRENT
    assert aging.status is FreshnessStatus.AGING


def test_stale_requires_explicit_policy() -> None:
    policy = FreshnessPolicy(
        aging_after=timedelta(hours=1),
        stale_after=timedelta(hours=24),
    )
    assessment = EvidenceFreshness.assess(
        "2026-09-28T11:59:59+00:00",
        reference_time="2026-09-29T12:00:00+00:00",
        policy=policy,
    )

    assert assessment.status is FreshnessStatus.STALE
    assert assessment.age_seconds is not None


def test_future_retrieval_is_unknown_not_current() -> None:
    policy = FreshnessPolicy(
        aging_after=timedelta(hours=1),
        stale_after=timedelta(hours=24),
    )
    assessment = EvidenceFreshness.assess(
        "2026-09-29T13:00:00+00:00",
        reference_time="2026-09-29T12:00:00+00:00",
        policy=policy,
    )

    assert assessment.status is FreshnessStatus.UNKNOWN


def test_timezone_is_required() -> None:
    policy = FreshnessPolicy(
        aging_after=timedelta(hours=1),
        stale_after=timedelta(hours=24),
    )
    with pytest.raises(ValueError, match="timezone"):
        EvidenceFreshness.assess(
            "2026-09-29T11:00:00",
            reference_time="2026-09-29T12:00:00+00:00",
            policy=policy,
        )


def test_policy_thresholds_are_validated() -> None:
    with pytest.raises(ValueError):
        FreshnessPolicy(
            aging_after=timedelta(hours=24),
            stale_after=timedelta(hours=1),
        )


def test_serialization_is_explicit() -> None:
    policy = FreshnessPolicy(
        aging_after=timedelta(hours=1),
        stale_after=timedelta(hours=24),
    )
    assessment = EvidenceFreshness.assess(
        "2026-09-29T11:00:00+00:00",
        reference_time="2026-09-29T12:00:00+00:00",
        policy=policy,
    )

    data = assessment.as_dict()

    assert data["status"] == "current"
    assert data["retrieved_at"] == "2026-09-29T11:00:00+00:00"
    assert data["reference_time"] == "2026-09-29T12:00:00+00:00"
