from datetime import date

from anne.core.evidence_semantics import EvidenceSemantics
from anne.core.source_verifier import SourceAwareVerifier, SourceRecord
from anne.core.verification import FactualStatus


def test_compound_claim_requires_all_atomic_claims():
    verifier = SourceAwareVerifier(
        (
            SourceRecord("https://example.com/a", "655 W panel Türkiye'de 4800 TL", "TR", date.today(), True, "official"),
            SourceRecord("https://example.com/b", "şu anda satışta", "TR", date.today(), True, "official"),
        ),
        required_scope="TR",
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4800 TL ve şu anda satışta",
        verifier,
    )
    assert result.status == FactualStatus.VERIFIED
    assert result.verified is True


def test_one_unverified_atomic_claim_prevents_verified_whole():
    verifier = SourceAwareVerifier(
        (
            SourceRecord("https://example.com/a", "655 W panel Türkiye'de 4800 TL", "TR", date.today(), True, "official"),
        ),
        required_scope="TR",
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4800 TL ve şu anda satışta",
        verifier,
    )
    assert result.status == FactualStatus.UNVERIFIED
    assert result.verified is False
