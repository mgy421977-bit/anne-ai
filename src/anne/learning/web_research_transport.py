"""Bounded transport policies for public-web research.

These primitives describe cache, retry, and backoff decisions without deciding
whether retrieved content is true, fresh, independent, or authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
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


__all__ = [
    "CacheDecision",
    "CacheDisposition",
    "CachePolicy",
    "RetryDisposition",
    "RetryPolicy",
]
