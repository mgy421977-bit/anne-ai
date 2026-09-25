from anne.core.evidence_validator import EvidenceValidator
from anne.core.requirements import EvidenceStatus
from anne.core.verification import ReferenceClaim, ReferenceVerifier
from anne.mythos.agent_swarm import AgentRole, EvidenceItem, EvidencePackage


def package(claim: str = "source finding") -> EvidencePackage:
    return EvidencePackage(
        mission_id="mission_test",
        agent_id="agent_test",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim=claim,
                source="https://example.com/source",
                evidence_kind="WEB_SOURCE",
                confidence=0.2,
                provenance="test",
            ),
        ),
    )


def test_mitos_evidence_is_unverified_without_independent_verifier():
    result = EvidenceValidator.assess((package(),))
    assert result.status == EvidenceStatus.UNVERIFIED
    assert result.verified is False
    assert result.evidence_count == 1


def test_independent_reference_can_establish_available():
    claim = "exact claim"
    verifier = ReferenceVerifier(
        (ReferenceClaim(claim=claim, source="registry:test", supported=True),)
    )
    result = EvidenceValidator.assess((package(claim),), claim=claim, verifier=verifier)
    assert result.status == EvidenceStatus.AVAILABLE
    assert result.verified is True
    assert result.sources == ("registry:test",)


def test_conflicting_package_blocks_even_before_verification():
    pkg = EvidencePackage(
        mission_id="mission_test",
        agent_id="agent_test",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim="a",
                source="https://example.com/a",
                evidence_kind="WEB_SOURCE",
                provenance="test",
            ),
        ),
        contradictions=("source A disagrees with source B",),
    )
    result = EvidenceValidator.assess((pkg,))
    assert result.status == EvidenceStatus.CONFLICTING
    assert result.verified is False
