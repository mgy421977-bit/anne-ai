"""Bounded joint inference over explicit evidence.

Joint inference combines multiple evidence items into a derived claim without
silently upgrading that claim to factual truth or action authority. Logical
validity, factual verification, and authority remain separate concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from anne.core.source_independence import SourceIndependence, SourceIndependenceAssessment
from anne.learning.evidence import EvidenceLedger, EvidenceStatus


class JointInferenceStatus(StrEnum):
    DERIVED = "derived"
    INSUFFICIENT_PREMISES = "insufficient_premises"
    CONFLICTING_PREMISES = "conflicting_premises"
    UNVERIFIED_PREMISES = "unverified_premises"


@dataclass(frozen=True)
class JointInference:
    """A derived claim with an explicit premise and provenance boundary."""

    claim: str
    evidence_ids: tuple[str, ...]
    status: JointInferenceStatus
    source_independence: SourceIndependenceAssessment
    verified_premises: int
    unverified_premises: int
    conflicting_premises: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "claim": self.claim,
            "evidence_ids": list(self.evidence_ids),
            "status": self.status.value,
            "source_independence": self.source_independence.as_dict(),
            "verified_premises": self.verified_premises,
            "unverified_premises": self.unverified_premises,
            "conflicting_premises": self.conflicting_premises,
            "reason": self.reason,
        }


class JointInferenceEngine:
    """Combine explicit premises while preserving epistemic uncertainty."""

    def infer(
        self,
        *,
        claim: str,
        evidence_ids: tuple[str, ...],
        ledger: EvidenceLedger,
    ) -> JointInference:
        if not claim.strip():
            raise ValueError("claim must not be empty")
        if not evidence_ids:
            return JointInference(
                claim=claim,
                evidence_ids=(),
                status=JointInferenceStatus.INSUFFICIENT_PREMISES,
                source_independence=SourceIndependence.assess(()),
                verified_premises=0,
                unverified_premises=0,
                conflicting_premises=0,
                reason="No explicit premises were supplied.",
            )

        entries = tuple(ledger.get(evidence_id) for evidence_id in evidence_ids)
        independence = SourceIndependence.assess(
            tuple(entry.provenance for entry in entries)
        )
        verified = sum(entry.status == EvidenceStatus.VERIFIED for entry in entries)
        conflicting = sum(entry.status == EvidenceStatus.CONFLICTING for entry in entries)
        unverified = len(entries) - verified - conflicting

        if conflicting:
            status = JointInferenceStatus.CONFLICTING_PREMISES
            reason = (
                "At least one premise is explicitly conflicting; "
                "the derived claim remains unresolved."
            )
        elif unverified:
            status = JointInferenceStatus.UNVERIFIED_PREMISES
            reason = (
                "The premises are not all verified; "
                "combining them does not establish factual truth."
            )
        else:
            status = JointInferenceStatus.DERIVED
            reason = (
                "The claim is derived from explicit premises. "
                "Logical derivation and source-family diversity do not by "
                "themselves establish truth or authority."
            )

        return JointInference(
            claim=claim,
            evidence_ids=evidence_ids,
            status=status,
            source_independence=independence,
            verified_premises=verified,
            unverified_premises=unverified,
            conflicting_premises=conflicting,
            reason=reason,
        )


__all__ = ["JointInference", "JointInferenceEngine", "JointInferenceStatus"]
