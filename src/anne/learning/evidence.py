"""Structured evidence records used by ANNE's learning/research layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


@dataclass(frozen=True)
class EvidenceItem:
    """A provenance-carrying, non-authoritative piece of evidence."""

    source: str
    claim: str
    kind: str
    provenance: str
    confidence: float
    passage: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not self.provenance.strip():
            raise ValueError("provenance must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


class EvidenceStatus(StrEnum):
    """Epistemic status for evidence retained by the cognitive workspace."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REFUTED = "refuted"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    """Traceable evidence attached to a claim without upgrading it to truth."""

    claim: str
    source: str
    provenance: str
    confidence: float
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    passage: str = ""
    retrieved_at: str = ""

    def __post_init__(self) -> None:
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.provenance.strip():
            raise ValueError("provenance must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        EvidenceStatus(self.status)
        if not self.retrieved_at:
            object.__setattr__(self, "retrieved_at", datetime.now(UTC).isoformat())


__all__ = ["EvidenceItem", "EvidenceLedgerEntry", "EvidenceStatus"]
