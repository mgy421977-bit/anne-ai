"""Bounded transport policies for public-web research.

These primitives describe cache, retry, and backoff decisions without deciding
whether retrieved content is true, fresh, independent, or authoritative.
"""
from __future__ import annotations

import time
import urllib.request
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class CacheDisposition(StrEnum):
    """Whether a cached response may be reused."""

    MISS = "miss"
    HIT = "hit"
    EXPIRED = "expired"


class RetryDisposition(StrEnum):
    """Whether a failed retrieval may be attempted again."""

    RETRY = "retry"
    STOP = "stop"


@dataclass(frozen=True)
class CachePolicy:
    """Explicit bounded cache policy."""

    ttl_seconds: float = 60.0
    max_entries: int = 64

    def __post_init__(self) -> None:
        if self.ttl_seconds < 0:
            raise ValueError("ttl_seconds must be non-negative")
        if self.max_entries < 1:
            raise ValueError("max_entries must be positive")


@dataclass(frozen=True)
class RetryPolicy:
    """Explicit bounded retry/backoff policy."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 4.0
    backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must be non-negative")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must cover initial delay")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")

    def delay_for_retry(self, attempt: int) -> float:
        """Return bounded delay before the next attempt."""
        if attempt < 1:
            raise ValueError("attempt must be positive")
        delay = self.initial_delay_seconds * (
            self.backoff_multiplier ** (attempt - 1)
        )
        return min(self.max_delay_seconds, delay)

    def disposition(self, attempt: int) -> RetryDisposition:
        """Return whether another attempt remains within the policy."""
        if attempt < 1:
            raise ValueError("attempt must be positive")
        return (
            RetryDisposition.RETRY
            if attempt < self.max_attempts
            else RetryDisposition.STOP
        )

    def as_dict(self) -> dict[str, float | int]:
        return {
            "max_attempts": self.max_attempts,
            "initial_delay_seconds": self.initial_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "backoff_multiplier": self.backoff_multiplier,
        }


@dataclass(frozen=True)
class CacheDecision:
    """Observable cache decision; it carries no factual authority."""

    disposition: CacheDisposition
    age_seconds: float | None
    policy: CachePolicy

    def as_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "age_seconds": self.age_seconds,
            "ttl_seconds": self.policy.ttl_seconds,
            "max_entries": self.policy.max_entries,
        }


@dataclass(frozen=True)
class TransportResult:
    """Retrieved payload plus bounded transport metadata."""

    content: str
    retrieved_at: str
    attempts: int
    cache: CacheDecision

    def as_dict(self) -> dict[str, object]:
        return {
            "retrieved_at": self.retrieved_at,
            "attempts": self.attempts,
            "cache": self.cache.as_dict(),
        }


@dataclass(frozen=True)
class _CacheEntry:
    content: str
    retrieved_at: datetime


class WebResearchTransport:
    """Bounded, provider-independent retrieval adapter."""

    def __init__(
        self,
        *,
        fetcher: Callable[[str], str] | None = None,
        cache_policy: CachePolicy | None = None,
        retry_policy: RetryPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.fetcher = fetcher or self._default_fetcher
        self.cache_policy = cache_policy or CachePolicy()
        self.retry_policy = retry_policy or RetryPolicy()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.sleeper = sleeper or time.sleep
        self.timeout_seconds = timeout_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()

    def _default_fetcher(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ANNE-AI/0.3 (+generic-public-web-research)"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read()
            if not isinstance(raw, bytes):
                raise TypeError("web response body must be bytes")
            return raw.decode("utf-8", errors="replace")

    def _cache_decision(
        self, entry: _CacheEntry | None, now: datetime
    ) -> CacheDecision:
        if entry is None:
            return CacheDecision(CacheDisposition.MISS, None, self.cache_policy)
        age = (now - entry.retrieved_at).total_seconds()
        if age < self.cache_policy.ttl_seconds:
            return CacheDecision(CacheDisposition.HIT, age, self.cache_policy)
        return CacheDecision(CacheDisposition.EXPIRED, age, self.cache_policy)

    def _store(self, url: str, content: str, retrieved_at: datetime) -> None:
        self._cache[url] = _CacheEntry(content, retrieved_at)
        self._cache.move_to_end(url)
        while len(self._cache) > self.cache_policy.max_entries:
            self._cache.popitem(last=False)

    def fetch(self, url: str) -> TransportResult:
        """Fetch a URL with bounded cache reuse and retry behavior."""
        if not url.strip():
            raise ValueError("url must not be empty")

        now = self.clock()
        entry = self._cache.get(url)
        decision = self._cache_decision(entry, now)
        if entry is not None and decision.disposition is CacheDisposition.HIT:
            self._cache.move_to_end(url)
            return TransportResult(
                content=entry.content,
                retrieved_at=entry.retrieved_at.isoformat(),
                attempts=0,
                cache=decision,
            )

        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                content = self.fetcher(url)
                retrieved_at = self.clock()
                self._store(url, content, retrieved_at)
                return TransportResult(
                    content=content,
                    retrieved_at=retrieved_at.isoformat(),
                    attempts=attempt,
                    cache=decision,
                )
            except Exception as exc:
                last_error = exc
                if (
                    self.retry_policy.disposition(attempt)
                    is RetryDisposition.STOP
                ):
                    raise
                self.sleeper(self.retry_policy.delay_for_retry(attempt))

        assert last_error is not None
        raise last_error


__all__ = [
    "CacheDecision",
    "CacheDisposition",
    "CachePolicy",
    "RetryDisposition",
    "RetryPolicy",
    "TransportResult",
    "WebResearchTransport",
]
