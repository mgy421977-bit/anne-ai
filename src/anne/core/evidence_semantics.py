"""Evidence semantics: validate atomic claims independently."""
from __future__ import annotations

from dataclasses import dataclass

from anne.core.claim_decomposer import AtomicClaim, ClaimDecomposer
from anne.core.source_verifier import SourceAwareVerifier
from anne.core.verification import FactualStatus


@dataclass(frozen=True)
class ClaimAssessment:
    claim: AtomicClaim
    status: FactualStatus
    sources: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ClaimSetAssessment:
    original: str
    claims: tuple[ClaimAssessment, ...]
    status: FactualStatus

    @property
    def verified(self) -> bool:
        return self.status == FactualStatus.VERIFIED


class EvidenceSemantics:
    """Decompose first, then verify every atomic proposition."""

    def __init__(self, decomposer: ClaimDecomposer | None = None) -> None:
        self.decomposer = decomposer or ClaimDecomposer()

    def assess(
        self,
        text: str,
        verifier: SourceAwareVerifier,
    ) -> ClaimSetAssessment:
        claim_set = self.decomposer.decompose(text)
        assessments: list[ClaimAssessment] = []

        for claim in claim_set.claims:
            result = verifier.verify(claim.text)
            assessments.append(
                ClaimAssessment(
                    claim=claim,
                    status=result.status,
                    sources=result.sources,
                    reason=result.reason,
                )
            )

        statuses = {item.status for item in assessments}
        if not assessments:
            status = FactualStatus.UNVERIFIED
        elif FactualStatus.CONFLICTING in statuses:
            status = FactualStatus.CONFLICTING
        elif FactualStatus.REFUTED in statuses:
            status = FactualStatus.REFUTED
        elif all(item.status == FactualStatus.VERIFIED for item in assessments):
            status = FactualStatus.VERIFIED
        else:
            status = FactualStatus.UNVERIFIED

        return ClaimSetAssessment(text, tuple(assessments), status)


__all__ = ["ClaimAssessment", "ClaimSetAssessment", "EvidenceSemantics"]
