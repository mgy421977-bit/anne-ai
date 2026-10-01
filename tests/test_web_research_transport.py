from anne.learning.web_research import WebResearcher
from anne.learning.web_research_transport import (
    CacheDecision,
    CacheDisposition,
    CachePolicy,
    RetryDisposition,
    RetryPolicy,
)


def test_cache_policy_is_explicit_and_bounded() -> None:
    policy = CachePolicy(ttl_seconds=30.0, max_entries=10)
    decision = CacheDecision(CacheDisposition.HIT, 4.0, policy)

    assert decision.disposition is CacheDisposition.HIT
    assert decision.age_seconds == 4.0
    assert decision.as_dict() == {
        "disposition": "hit",
        "age_seconds": 4.0,
        "ttl_seconds": 30.0,
        "max_entries": 10,
    }


def test_cache_policy_rejects_invalid_bounds() -> None:
    for kwargs in (
        {"ttl_seconds": -1},
        {"max_entries": 0},
    ):
        try:
            CachePolicy(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid cache policy must fail closed")


def test_retry_policy_is_bounded_with_exponential_backoff() -> None:
    policy = RetryPolicy(
        max_attempts=4,
        initial_delay_seconds=0.5,
        max_delay_seconds=2.0,
        backoff_multiplier=2.0,
    )

    assert policy.disposition(1) is RetryDisposition.RETRY
    assert policy.disposition(3) is RetryDisposition.RETRY
    assert policy.disposition(4) is RetryDisposition.STOP
    assert policy.delay_for_retry(1) == 0.5
    assert policy.delay_for_retry(2) == 1.0
    assert policy.delay_for_retry(3) == 2.0
    assert policy.delay_for_retry(4) == 2.0


def test_retry_policy_rejects_invalid_configuration() -> None:
    invalid = (
        {"max_attempts": 0},
        {"initial_delay_seconds": -1},
        {"initial_delay_seconds": 2, "max_delay_seconds": 1},
        {"backoff_multiplier": 0.5},
    )
    for kwargs in invalid:
        try:
            RetryPolicy(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid retry policy must fail closed")


def test_transport_policies_do_not_create_factual_authority() -> None:
    cache = CacheDecision(
        CacheDisposition.EXPIRED,
        120.0,
        CachePolicy(ttl_seconds=60.0),
    )
    retry = RetryPolicy(max_attempts=2)

    assert cache.disposition is CacheDisposition.EXPIRED
    assert retry.disposition(2) is RetryDisposition.STOP
    assert "verified" not in cache.as_dict()
    assert "authority" not in cache.as_dict()


def test_transport_rejects_invalid_timeout() -> None:
    import pytest

    with pytest.raises(ValueError, match="timeout_seconds"):
        WebResearchTransport(timeout_seconds=0)
