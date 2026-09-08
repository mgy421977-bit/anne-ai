"""Factual verification contracts, separate from ANLA's lexical heuristics.

Reference records must come from a trusted application or independent evaluator,
never from a model-produced semantic frame. Exact matching deliberately abstains
on paraphrases, partial support and unrecognized claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol


class FactualStatus(StrEnum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class VerificationResult:
    status: FactualStatus = FactualStatus.UNVERIFIED
    sources: tuple[str, ...] = ()
    reason: str = "No independent factual verifier supplied."

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ClaimVerifier(Protocol):
    def verify(self, claim: str) -> VerificationResult: ...


@dataclass(frozen=True)
class ReferenceClaim:
    claim: str
    source: str
    supported: bool

    def __post_init__(self) -> None:
        if not self.claim.strip() or not self.source.strip():
            raise ValueError("A reference requires a claim and source provenance")
        if not isinstance(self.supported, bool):
            raise ValueError("supported must be a boolean")


class ReferenceVerifier:
    """Bounded exact-claim adapter, not a general-purpose fact checker."""

    def __init__(self, references: tuple[ReferenceClaim, ...] = ()) -> None:
        self.references = tuple(references)

    @staticmethod
    def normalize(claim: str) -> str:
        return " ".join(claim.split())

    def verify(self, claim: str) -> VerificationResult:
        matches = [
            reference for reference in self.references
            if self.normalize(reference.claim) == self.normalize(claim)
        ]
        if not matches:
            return VerificationResult(reason="No matching independent reference.")
        sources = tuple(sorted({reference.source for reference in matches}))
        verdicts = {reference.supported for reference in matches}
        if len(verdicts) > 1:
            return VerificationResult(FactualStatus.CONFLICTING, sources, "References disagree.")
        status = FactualStatus.VERIFIED if True in verdicts else FactualStatus.REFUTED
        return VerificationResult(status, sources, "Exact claim checked against reference records.")


def verify_claim(claim: str, verifier: ClaimVerifier | None = None) -> VerificationResult:
    """Fail closed on verifier failures, malformed statuses or absent provenance."""
    if verifier is None:
        return VerificationResult()
    try:
        result = verifier.verify(claim)
        if not isinstance(result, VerificationResult) or not isinstance(result.sources, tuple):
            return VerificationResult(reason="Malformed independent verifier result.")
        status = FactualStatus(result.status)
        if status != FactualStatus.UNVERIFIED and (
            not result.sources
            or any(not isinstance(source, str) or not source.strip() for source in result.sources)
        ):
            return VerificationResult(reason="Verifier result lacks provenance.")
        return VerificationResult(status, tuple(result.sources), result.reason)
    except Exception:
        return VerificationResult(reason="Independent verifier failed; no factual assurance.")