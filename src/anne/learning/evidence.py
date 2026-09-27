"""Structured evidence records used by ANNE's learning/research layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SupportStatus(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class EvidenceItem:
    """A provenance-carrying, non-authoritative piece of evidence."""

    source: str
    claim: str
    kind: str
    provenance: str
    confidence: float
    passage: str = ""
    support: str = SupportStatus.UNCLEAR.value

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


@dataclass(frozen=True)
class EvidenceDependency:
    """Link a derived claim to the evidence identifiers it depends on."""

    claim_id: str
    claim: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id must not be empty")
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must contain non-empty identifiers")


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
    support: str = SupportStatus.UNCLEAR.value

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


__all__ = ["EvidenceItem", "EvidenceLedgerEntry", "EvidenceDependency", "EvidenceStatus", "SupportStatus"]
