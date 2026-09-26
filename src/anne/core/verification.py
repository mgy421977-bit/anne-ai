"""Factual verification contracts, separate from ANLA's lexical heuristics.

Reference records must come from a trusted application or independent evaluator,
never from a model-produced semantic frame. Exact matching deliberately abstains
on paraphrases, partial support and unrecognized claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlparse


class FactualStatus(StrEnum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


class SupportStatus(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class VerificationResult:
    status: FactualStatus = FactualStatus.UNVERIFIED
    sources: tuple[str, ...] = ()
    reason: str = "No independent factual verifier supplied."
    trace: tuple[dict[str, str], ...] = ()

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


class BoundedMultiSourceVerifier:
    """Deterministic corroboration over an explicit evidence set.

    Evidence must carry an explicit support label from a trusted upstream
    classifier. A single source, an unclear passage, or duplicated domains
    never becomes VERIFIED. This is bounded corroboration, not a general
    semantic fact checker.
    """

    def __init__(self, evidence: tuple[Any, ...] = ()) -> None:
        self.evidence = tuple(evidence)

    def verify_evidence(self, claim: str, evidence: tuple[Any, ...]) -> VerificationResult:
        return BoundedMultiSourceVerifier(tuple(evidence)).verify(claim)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.split()).casefold()

    @staticmethod
    def _identity(provenance: str) -> str:
        parsed = urlparse(provenance)
        return (parsed.netloc or parsed.path.split("/", 1)[0]).casefold()

    def verify(self, claim: str) -> VerificationResult:
        normalized = self._normalize(claim)
        rows: list[dict[str, str]] = []
        usable: list[tuple[str, str]] = []
        for item in self.evidence:
            item_claim = getattr(item, "claim", "")
            provenance = getattr(item, "provenance", "")
            passage = getattr(item, "passage", "")
            support = str(getattr(item, "support", SupportStatus.UNCLEAR)).lower()
            if not isinstance(item_claim, str) or self._normalize(item_claim) != normalized:
                continue
            if not isinstance(provenance, str) or not provenance.strip() or not isinstance(passage, str) or not passage.strip():
                continue
            try:
                support = SupportStatus(support).value
            except ValueError:
                support = SupportStatus.UNCLEAR.value
            identity = self._identity(provenance)
            if not identity:
                continue
            usable.append((identity, support))
            rows.append({
                "claim": claim,
                "source": str(getattr(item, "source", "")),
                "provenance": provenance,
                "passage": passage,
                "support": support,
            })

        independent: dict[str, set[str]] = {}
        for identity, support in usable:
            independent.setdefault(support, set()).add(identity)
        supports = independent.get(SupportStatus.SUPPORTS.value, set())
        contradicts = independent.get(SupportStatus.CONTRADICTS.value, set())
        sources = tuple(sorted({row["provenance"] for row in rows}))
        if supports and contradicts:
            status = FactualStatus.CONFLICTING
            reason = "Independent sources support and contradict the claim."
        elif len(supports) >= 2:
            status = FactualStatus.VERIFIED
            reason = "Two independent sources support the claim."
        elif len(contradicts) >= 2:
            status = FactualStatus.REFUTED
            reason = "Two independent sources contradict the claim."
        else:
            status = FactualStatus.UNVERIFIED
            reason = "Insufficient independent claim support."
        return VerificationResult(status, sources, reason, tuple(rows))


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
