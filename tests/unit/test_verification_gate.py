"""Unit coverage for the explicit verification gate."""

from anne.core.verification import FactualStatus, ReferenceClaim, ReferenceVerifier
from anne.core.verification_gate import (
    VerificationGate,
    VerificationGateStatus,
)


def verifier(*supported: bool) -> ReferenceVerifier:
    return ReferenceVerifier(
        tuple(
            ReferenceClaim(
                claim="the sky is blue",
                source=f"source-{index}",
                supported=value,
            )
            for index, value in enumerate(supported)
        )
    )


def test_two_independent_supporting_references_pass_gate():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(True, True),
    )

    assert result.status is VerificationGateStatus.VERIFIED
    assert result.execution_allowed is True
    assert result.verification.status is FactualStatus.VERIFIED


def test_unverified_claim_is_blocked():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(True),
    )

    assert result.status is VerificationGateStatus.BLOCKED
    assert result.execution_allowed is False


def test_conflicting_evidence_requires_review():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(True, False),
    )

    assert result.status is VerificationGateStatus.REVIEW
    assert result.execution_allowed is False
    assert result.verification.status is FactualStatus.CONFLICTING


def test_refuted_claim_is_blocked():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(False, False),
    )

    assert result.status is VerificationGateStatus.BLOCKED
    assert result.verification.status is FactualStatus.REFUTED


def test_missing_selection_cannot_pass_gate():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(True, True),
        selected=False,
    )

    assert result.status is VerificationGateStatus.BLOCKED
    assert result.execution_allowed is False


def test_empty_claim_cannot_pass_gate():
    result = VerificationGate().evaluate("", verifier=verifier(True, True))

    assert result.status is VerificationGateStatus.BLOCKED


def test_serialization_exposes_execution_boundary():
    result = VerificationGate().evaluate(
        "the sky is blue",
        verifier=verifier(True, True),
    )
    payload = result.as_dict()

    assert payload["execution_allowed"] is True
    assert payload["verification"]["status"] == "verified"
