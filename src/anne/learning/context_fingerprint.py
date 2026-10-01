"""Deterministic fingerprints for explicitly observed runtime context.

This module never derives context from confidence, outcomes, or semantics. It
only normalizes fields that the runtime explicitly recorded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ExplicitContextFingerprint:
    """Bounded, deterministic representation of explicit runtime context."""

    key: str = ""
    conditions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(
            sorted(
                {
                    (str(key), str(value))
                    for key, value in self.conditions
                    if str(key).strip()
                }
            )
        )
        object.__setattr__(self, "key", str(self.key))
        object.__setattr__(self, "conditions", normalized)

    @classmethod
    def from_context(
        cls,
        context: Mapping[str, object] | None,
        *,
        max_conditions: int = 16,
    ) -> ExplicitContextFingerprint:
        if max_conditions < 1:
            raise ValueError("max_conditions must be positive")
        data = dict(context or {})
        key = data.get("key", "")
        raw_conditions = data.get("conditions", {})
        if not isinstance(raw_conditions, Mapping):
            raw_conditions = {}
        conditions = tuple(
            sorted(
                (str(k), str(v))
                for k, v in raw_conditions.items()
                if str(k).strip()
            )
        )
        return cls(str(key), conditions[:max_conditions])


__all__ = ["ExplicitContextFingerprint"]
