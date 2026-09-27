"""Explicit verification gate between selection and execution.

Selection is not verification. This gate makes that boundary executable:
only a verified claim may pass the factual gate; conflicting, refuted,
unverified, or malformed verification results remain blocked/reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from anne.core.verification import FactualStatus, VerificationResult, verify_claim


class VerificationGateStatus(StrEnum):
    VERIFIED = "verified"
    BLOCKED = "blocked"
    REVIEW = "review"


@dataclass(frozen=True)
class VerificationGateResult:
    status: VerificationGateStatus
    verification: VerificationResult
    claim: str
    next_action: tuple[str, ...]

    @property
    def execution_allowed(self) -> bool:
        return self.status is VerificationGateStatus.VERIFIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "claim": self.claim,
            "execution_allowed": self.execution_allowed,
            "verification": self.verification.as_dict(),
            "next_action": list(self.next_action),
        }


class VerificationGate:
    """Fail-closed gate for factual assurance after candidate selection."""

    def __init__(self, *, require_provenance: bool = True) -> None:
        self.require_provenance = require_provenance

    def evaluate(
        self,
        claim: str,
        *,
        verifier: Any = None,
        selected: bool = True,
    ) -> VerificationGateResult:
        if not selected:
            return VerificationGateResult(
                VerificationGateStatus.BLOCKED,
                VerificationResult(reason="No candidate was selected."),
                claim,
                ("Select a candidate before requesting factual verification.",),
            )

        if not isinstance(claim, str) or not claim.strip():
            return VerificationGateResult(
                VerificationGateStatus.BLOCKED,
                VerificationResult(reason="Empty claim cannot be verified."),
                claim if isinstance(claim, str) else "",
                ("Provide a concrete claim before verification.",),
            )

        result = verify_claim(claim, verifier)
        if (
            self.require_provenance
            and result.status is not FactualStatus.UNVERIFIED
            and not result.sources
        ):
            result = VerificationResult(
                reason="Verification lacks independent provenance."
            )

        if result.status is FactualStatus.VERIFIED:
            return VerificationGateResult(
                VerificationGateStatus.VERIFIED,
                result,
                claim,
                (
                    "Factual gate passed.",
                    "Continue to downstream safety, authority, and execution gates.",
                ),
            )

        if result.status is FactualStatus.CONFLICTING:
            return VerificationGateResult(
                VerificationGateStatus.REVIEW,
                result,
                claim,
                (
                    "Do not execute while independent evidence conflicts.",
                    "Resolve the evidence conflict and verify again.",
                ),
            )

        if result.status is FactualStatus.REFUTED:
            return VerificationGateResult(
                VerificationGateStatus.BLOCKED,
                result,
                claim,
                (
                    "Do not execute the refuted claim.",
                    "Reframe or select an evidence-backed alternative.",
                ),
            )

        return VerificationGateResult(
            VerificationGateStatus.BLOCKED,
            result,
            claim,
            (
                "Do not execute an unverified claim.",
                "Acquire independent evidence or abstain.",
            ),
        )


__all__ = [
    "VerificationGate",
    "VerificationGateResult",
    "VerificationGateStatus",
]
