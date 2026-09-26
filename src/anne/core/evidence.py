"""Evidence enforcement for ANNE's bounded cognitive pipeline.

Memory matches are references, not proof.  This gate prevents evidence-required
cycles from producing an authoritative decision unless evidence has been
explicitly verified by a future trusted evidence provider.
"""

from __future__ import annotations

from anne.core.requirements import EvidenceStatus
from anne.core.verification import FactualStatus, VerificationResult


def evidence_status_from_verification(result: VerificationResult) -> EvidenceStatus:
    """Map an independent verification result without manufacturing evidence.

    ``AVAILABLE`` is a controlled transition: it is reachable only from an
    explicitly verified result carrying non-empty provenance. Search results,
    memory records, MITOS candidates, model confidence, malformed verifier
    output, and verifier exceptions remain non-authoritative.
    """
    if not isinstance(result, VerificationResult):
        return EvidenceStatus.UNVERIFIED

    try:
        status = FactualStatus(result.status)
    except (TypeError, ValueError):
        return EvidenceStatus.UNVERIFIED

    if status is FactualStatus.VERIFIED:
        if not result.sources or any(
            not isinstance(source, str) or not source.strip() for source in result.sources
        ):
            return EvidenceStatus.UNVERIFIED
        return EvidenceStatus.AVAILABLE
    if status is FactualStatus.REFUTED:
        return EvidenceStatus.REFUTED
    if status is FactualStatus.CONFLICTING:
        return EvidenceStatus.CONFLICTING
    return EvidenceStatus.UNVERIFIED


class EvidenceGate:
    """Conservative gate between context retrieval and decision output."""

    BLOCKING = frozenset(
        {
            EvidenceStatus.MISSING,
            EvidenceStatus.UNVERIFIED,
            EvidenceStatus.CONFLICTING,
            EvidenceStatus.REFUTED,
        }
    )

    @classmethod
    def allows_decision(cls, *, required: bool, status: str) -> bool:
        if not required:
            return True
        try:
            evidence_status = EvidenceStatus(status)
        except ValueError:
            return False
        return evidence_status not in cls.BLOCKING and evidence_status == EvidenceStatus.AVAILABLE

    @classmethod
    def reason(cls, status: str) -> str:
        if status == EvidenceStatus.MISSING:
            return "Evidence is required but no evidence reference is available."
        if status == EvidenceStatus.UNVERIFIED:
            return "Evidence references exist, but they have not been independently verified."
        if status == EvidenceStatus.CONFLICTING:
            return "Evidence references conflict and cannot support a bounded decision."
        if status == EvidenceStatus.REFUTED:
            return "Evidence was independently refuted and cannot support a bounded decision."
        return "Evidence requirement was not satisfied by a trusted evidence state."


__all__ = ["EvidenceGate", "evidence_status_from_verification"]
