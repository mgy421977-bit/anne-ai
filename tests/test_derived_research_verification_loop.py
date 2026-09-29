from anne.core.verification import BoundedMultiSourceVerifier, FactualStatus
from anne.learning.evidence import EvidenceItem


def test_verification_fixture_requires_two_independent_sources() -> None:
    claim = "A and B jointly support X"
    evidence = (
        EvidenceItem(
            source="source-a",
            claim=claim,
            kind="web",
            provenance="https://alpha.example/a",
            confidence=0.8,
            passage=claim,
        ),
        EvidenceItem(
            source="source-b",
            claim=claim,
            kind="web",
            provenance="https://beta.example/b",
            confidence=0.8,
            passage=f"Independent source confirms: {claim}",
        ),
    )
    result = BoundedMultiSourceVerifier().verify_evidence(claim, evidence)
    assert result.status == FactualStatus.VERIFIED
    assert len(result.sources) == 2
