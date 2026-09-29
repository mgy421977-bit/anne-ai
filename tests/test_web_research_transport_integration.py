from __future__ import annotations

from datetime import datetime, timezone

import pytest

from anne.learning.web_research_transport import (
    CacheDisposition,
    RetryPolicy,
    TransportResult,
    WebResearchTransport,
)


def test_transport_uses_cache_within_ttl() -> None:
    calls: list[str] = []
    now = datetime(2026, 9, 29, 5, 0, tzinfo=timezone.utc)

    def fetcher(url: str) -> str:
        calls.append(url)
        return "payload"

    transport = WebResearchTransport(
        fetcher=fetcher,
        cache_ttl_seconds=60,
        clock=lambda: now,
    )

    first = transport.fetch("https://example.com/a")
    second = transport.fetch("https://example.com/a")

    assert first.content == "payload"
    assert first.cache.disposition is CacheDisposition.MISS
    assert second.cache.disposition is CacheDisposition.HIT
    assert second.content == "payload"
    assert second.retrieved_at == first.retrieved_at
    assert calls == ["https://example.com/a"]


def test_expired_cache_retrieves_fresh_content() -> None:
    calls = 0
    now = [datetime(2026, 9, 29, 5, 0, tzinfo=timezone.utc)]

    def fetcher(url: str) -> str:
        nonlocal calls
        calls += 1
        return f"payload-{calls}"

    transport = WebResearchTransport(
        fetcher=fetcher,
        cache_ttl_seconds=60,
        clock=lambda: now[0],
    )

    first = transport.fetch("https://example.com/a")
    now[0] = datetime(2026, 9, 29, 5, 2, tzinfo=timezone.utc)
    second = transport.fetch("https://example.com/a")

    assert first.cache.disposition is CacheDisposition.MISS
    assert second.cache.disposition is CacheDisposition.EXPIRED
    assert second.content == "payload-2"
    assert second.retrieved_at != first.retrieved_at


def test_transport_retries_with_bounded_backoff() -> None:
    attempts = 0
    sleeps: list[float] = []

    def fetcher(url: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    transport = WebResearchTransport(
        fetcher=fetcher,
        retry_policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.25,
            max_delay_seconds=0.5,
            backoff_multiplier=2,
        ),
        sleeper=sleeps.append,
    )

    result = transport.fetch("https://example.com/retry")

    assert result.content == "ok"
    assert result.attempts == 3
    assert sleeps == [0.25, 0.5]


def test_transport_stops_after_retry_budget() -> None:
    attempts = 0

    def fetcher(url: str) -> str:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("persistent")

    transport = WebResearchTransport(
        fetcher=fetcher,
        retry_policy=RetryPolicy(max_attempts=2),
        sleeper=lambda _: None,
    )

    with pytest.raises(TimeoutError, match="persistent"):
        transport.fetch("https://example.com/fail")

    assert attempts == 2


def test_transport_result_exposes_metadata_without_authority() -> None:
    transport = WebResearchTransport(
        fetcher=lambda _: "ok",
        clock=lambda: datetime(2026, 9, 29, 5, 0, tzinfo=timezone.utc),
    )

    result: TransportResult = transport.fetch("https://example.com/a")

    assert result.retrieved_at.endswith("+00:00")
    assert result.attempts == 1
    assert "verified" not in result.as_dict()
    assert "authority" not in result.as_dict()
