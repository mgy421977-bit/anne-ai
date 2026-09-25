"""Source-aware independent evidence verification.

The verifier does not decide truth from model confidence. It consumes explicit
source records and deterministic metadata checks. Unknown, stale, out-of-scope,
or mismatched evidence remains UNVERIFIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from anne.core.verification import (
    ClaimVerifier,
    FactualStatus,
    VerificationResult,
)


@dataclass(frozen=True)
class SourceRecord:
    source: str
    claim: str
    scope: str = ""
    published_date: date | None = None
    supported: bool = True
    authority_level: str = "unknown"

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.claim.strip():
            raise ValueError("source and claim are required")
        parsed = urlparse(self.source)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("source must be an absolute URL or URI")


class SourceAwareVerifier(ClaimVerifier):
    """Deterministic verifier for explicitly supplied source records."""

    def __init__(
        self,
        records: tuple[SourceRecord, ...] = (),
        *,
        required_scope: str | None = None,
        max_age_days: int | None = None,
        allowed_authorities: tuple[str, ...] = (),
    ) -> None:
        self.records = tuple(records)
        self.required_scope = required_scope
        self.max_age_days = max_age_days
        self.allowed_authorities = tuple(a.casefold() for a in allowed_authorities)

    @staticmethod
    def _claim_matches(expected: str, actual: str) -> bool:
        return " ".join(expected.split()).casefold() == " ".join(actual.split()).casefold()

    def verify(self, claim: str) -> VerificationResult:
        matches = [
            record for record in self.records
            if self._claim_matches(record.claim, claim)
        ]
        if not matches:
            return VerificationResult(reason="No source record matches the claim.")

        accepted: list[SourceRecord] = []
        rejected: list[str] = []

        for record in matches:
            if self.required_scope and record.scope != self.required_scope:
                rejected.append(f"{record.source}: scope mismatch")
                continue

            if self.allowed_authorities:
                if record.authority_level.casefold() not in self.allowed_authorities:
                    rejected.append(f"{record.source}: authority not allowed")
                    continue

            if self.max_age_days is not None and record.published_date is not None:
                age = (date.today() - record.published_date).days
                if age < 0 or age > self.max_age_days:
                    rejected.append(f"{record.source}: outside date window")
                    continue

            accepted.append(record)

        if not accepted:
            return VerificationResult(
                FactualStatus.UNVERIFIED,
                tuple(record.source for record in matches),
                "; ".join(rejected) or "Matching sources failed verification constraints.",
            )

        verdicts = {record.supported for record in accepted}
        sources = tuple(dict.fromkeys(record.source for record in accepted))

        if len(verdicts) > 1:
            return VerificationResult(
                FactualStatus.CONFLICTING,
                sources,
                "Accepted sources disagree about the claim.",
            )

        status = FactualStatus.VERIFIED if True in verdicts else FactualStatus.REFUTED
        return VerificationResult(
            status,
            sources,
            "Claim matched accepted source records and passed scope/date/authority checks.",
        )


__all__ = ["SourceAwareVerifier", "SourceRecord"]
