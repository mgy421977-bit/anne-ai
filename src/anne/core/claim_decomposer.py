"""Deterministic claim decomposition for ANNE evidence validation.

A claim is split into atomic, independently verifiable propositions. This is
deliberately conservative: decomposition never establishes truth.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AtomicClaim:
    id: str
    text: str
    predicate: str = "statement"
    value: str | None = None
    qualifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimSet:
    original: str
    claims: tuple[AtomicClaim, ...]

    @property
    def complete(self) -> bool:
        return bool(self.claims)


class ClaimDecomposer:
    """Small inspectable rule engine for common factual claim structures."""

    _SEP = re.compile(r"\s+(?:ve|and|,|;|\+|/|aynı zamanda|ayrıca)\s+", re.I)
    _CURRENCY_VALUE = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(?:₺|tl|try|usd|eur|€|\$)|"
        r"(?:₺|tl|try|usd|eur|€|\$)\s*(\d+(?:[.,]\d+)?)",
        re.I,
    )

    def decompose(self, text: str) -> ClaimSet:
        original = " ".join(text.split())
        if not original:
            return ClaimSet("", ())

        parts = [p.strip(" .") for p in self._SEP.split(original) if p.strip(" .")]
        claims: list[AtomicClaim] = []

        for index, part in enumerate(parts, start=1):
            predicate = "statement"
            value: str | None = None
            qualifiers: list[str] = []
            lowered = part.casefold()

            if re.search(r"\b(?:tl|try|usd|eur|€|\$)\b", lowered) or re.search(
                r"\b\d+[.,]?\d*\s*(?:tl|w|kw|kwh|mw|gw)\b", lowered
            ):
                predicate = "value"

            if any(x in lowered for x in ("türkiye", "turkey", "tr pazarı", "türkiye'de")):
                qualifiers.append("market:TR")
            if any(x in lowered for x in ("güncel", "şu anda", "today", "current", "2026")):
                qualifiers.append("time:current")
            if any(x in lowered for x in ("mevcut", "stokta", "available", "satışta")):
                qualifiers.append("availability:current")

            currency_match = self._CURRENCY_VALUE.search(part)
            if currency_match and predicate == "value":
                value = currency_match.group(1) or currency_match.group(2)
            else:
                number = re.search(
                    r"(?:₺|tl|try|usd|eur|€|\$)?\s*(\d+(?:[.,]\d+)?)",
                    part,
                    re.I,
                )
                if number and predicate == "value":
                    value = number.group(1)

            claims.append(
                AtomicClaim(
                    id=f"c{index}",
                    text=part,
                    predicate=predicate,
                    value=value,
                    qualifiers=tuple(qualifiers),
                )
            )

        return ClaimSet(original, tuple(claims))


__all__ = ["AtomicClaim", "ClaimSet", "ClaimDecomposer"]
