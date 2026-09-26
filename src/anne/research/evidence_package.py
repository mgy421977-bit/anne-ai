"""Evidence package bridge from research into ANNE's cognitive boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from anne.core.verification import FactualStatus, VerificationResult
from anne.research.web_search import WebSearchResult


@dataclass(frozen=True)
class ResearchEvidencePackage:
    """Explicit provenance bundle consumed by ANNE.

    Candidate research remains unverified. Only an independent verification
    result can promote the package to a decision-eligible state.
    """

    mission_id: str
    claims: tuple[str, ...]
    sources: tuple[str, ...]
    source_records: tuple[WebSearchResult, ...]
    factual_status: FactualStatus = FactualStatus.UNVERIFIED
    evidence_status: str = "unverified"
    verification_reason: str = ""
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_report(cls, report: Any) -> "ResearchEvidencePackage":
        sources = tuple(sorted({result.url for result in report.sources if result.url.strip()}))
        return cls(
            mission_id=report.mission_id,
            claims=tuple([report.objective]),
            sources=sources,
            source_records=tuple(report.sources),
            factual_status=FactualStatus.UNVERIFIED,
            evidence_status="unverified" if sources else "missing",
            verification_reason="Research sources are candidates until independently verified.",
        )

    def with_verification(self, result: VerificationResult) -> "ResearchEvidencePackage":
        if result.status != FactualStatus.UNVERIFIED and not result.sources:
            raise ValueError("verified research evidence requires provenance")
        status = "available" if result.status == FactualStatus.VERIFIED else (
            "conflicting" if result.status == FactualStatus.CONFLICTING else "unverified"
        )
        return ResearchEvidencePackage(
            mission_id=self.mission_id,
            claims=self.claims,
            sources=tuple(sorted(set(self.sources) | set(result.sources))),
            source_records=self.source_records,
            factual_status=result.status,
            evidence_status=status,
            verification_reason=result.reason,
            metadata=self.metadata,
        )


def apply_evidence_package(state: Any, package: ResearchEvidencePackage) -> Any:
    """Attach research provenance to CognitiveState without bypassing EvidenceGate."""
    state.evidence_status = package.evidence_status
    state.evidence_count = len(package.sources)
    state.evidence_verified = package.factual_status == FactualStatus.VERIFIED
    state.context_map["research_evidence"] = {
        "mission_id": package.mission_id,
        "claims": package.claims,
        "sources": package.sources,
        "factual_status": package.factual_status.value,
        "evidence_status": package.evidence_status,
        "verification_reason": package.verification_reason,
    }
    return state


__all__ = ["ResearchEvidencePackage", "apply_evidence_package"]
