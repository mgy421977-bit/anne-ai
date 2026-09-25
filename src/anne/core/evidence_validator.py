"""Evidence-package assessment for ANNE.

MITOS may discover evidence, but discovery is not verification. This module
bridges EvidencePackage records into ANNE's evidence state without promoting
public-web findings to FACT.
"""
from __future__ import annotations

from dataclasses import dataclass

from anne.mythos.agent_swarm import EvidencePackage
from anne.core.requirements import EvidenceStatus
from anne.core.verification import ClaimVerifier, FactualStatus, verify_claim
from anne.core.evidence_semantics import EvidenceSemantics
from anne.core.source_verifier import SourceAwareVerifier


@dataclass(frozen=True)
class EvidenceAssessment:
    status: EvidenceStatus
    evidence_count: int
    verified: bool
    sources: tuple[str, ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "evidence_count": self.evidence_count,
            "verified": self.verified,
            "sources": list(self.sources),
            "reason": self.reason,
        }


class EvidenceValidator:
    """Conservatively assess MITOS evidence before the ANLA decision gate."""

    @staticmethod
    def assess(
        packages: tuple[EvidencePackage, ...] | list[EvidencePackage] = (),
        *,
        claim: str | None = None,
        verifier: ClaimVerifier | None = None,
    ) -> EvidenceAssessment:
        valid_packages: list[EvidencePackage] = []
        for package in packages:
            package.validate()
            valid_packages.append(package)

        findings = [
            finding
            for package in valid_packages
            for finding in package.findings
            if finding.source.strip()
        ]
        sources = tuple(dict.fromkeys(finding.source for finding in findings))

        if any(package.contradictions for package in valid_packages):
            return EvidenceAssessment(
                EvidenceStatus.CONFLICTING,
                len(findings),
                False,
                sources,
                "MITOS reported contradictory evidence.",
            )

        if verifier is not None and claim:
            if isinstance(verifier, SourceAwareVerifier):
                semantic = EvidenceSemantics().assess(claim, verifier)
                semantic_sources = tuple(
                    source
                    for item in semantic.claims
                    for source in item.sources
                )
                if semantic.status == FactualStatus.VERIFIED:
                    return EvidenceAssessment(
                        EvidenceStatus.AVAILABLE,
                        len(findings),
                        True,
                        tuple(dict.fromkeys(semantic_sources)) or sources,
                        "All atomic claims passed independent source verification.",
                    )
                if semantic.status in {FactualStatus.REFUTED, FactualStatus.CONFLICTING}:
                    return EvidenceAssessment(
                        EvidenceStatus.CONFLICTING,
                        len(findings),
                        False,
                        tuple(dict.fromkeys(semantic_sources)) or sources,
                        "At least one atomic claim was refuted or conflicting.",
                    )
                return EvidenceAssessment(
                    EvidenceStatus.UNVERIFIED,
                    len(findings),
                    False,
                    tuple(dict.fromkeys(semantic_sources)) or sources,
                    "Atomic claim verification did not establish the complete claim.",
                )

            result = verify_claim(claim, verifier)
            if result.status == FactualStatus.VERIFIED:
                return EvidenceAssessment(
                    EvidenceStatus.AVAILABLE,
                    len(findings),
                    True,
                    result.sources or sources,
                    result.reason,
                )
            if result.status in {FactualStatus.REFUTED, FactualStatus.CONFLICTING}:
                return EvidenceAssessment(
                    EvidenceStatus.CONFLICTING,
                    len(findings),
                    False,
                    result.sources or sources,
                    result.reason,
                )

        if findings:
            return EvidenceAssessment(
                EvidenceStatus.UNVERIFIED,
                len(findings),
                False,
                sources,
                "Evidence exists, but independent factual verification has not passed.",
            )

        return EvidenceAssessment(
            EvidenceStatus.MISSING,
            0,
            False,
            (),
            "No evidence package supplied a usable source finding.",
        )


__all__ = ["EvidenceAssessment", "EvidenceValidator"]
