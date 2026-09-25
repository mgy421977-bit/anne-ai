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

def test_realistic_panel_price_claim_reports_atomic_evidence():
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/panel",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                True,
                "official",
            ),
            SourceRecord(
                "https://example.com/stock",
                "şu anda satışta",
                "TR",
                date.today(),
                True,
                "official",
            ),
        ),
        required_scope="TR",
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        verifier,
    )

    assert result.status == FactualStatus.VERIFIED
    assert result.verified is True
    assert len(result.claims) == 2
    assert all(item.status == FactualStatus.VERIFIED for item in result.claims)

def test_conflicting_sources_block_verification():
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/source-a",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                True,
                "official",
            ),
            SourceRecord(
                "https://example.com/source-b",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                False,
                "official",
            ),
            SourceRecord(
                "https://example.com/stock",
                "şu anda satışta",
                "TR",
                date.today(),
                True,
                "official",
            ),
        ),
        required_scope="TR",
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        verifier,
    )

    assert result.status == FactualStatus.CONFLICTING
    assert result.verified is False
    price_claim = next(item for item in result.claims if item.claim.value == "4.800")
    assert price_claim.status == FactualStatus.CONFLICTING

def test_stale_source_does_not_verify_current_claim():
    from datetime import timedelta

    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/old-panel-price",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today() - timedelta(days=800),
                True,
                "official",
            ),
            SourceRecord(
                "https://example.com/current-stock",
                "şu anda satışta",
                "TR",
                date.today(),
                True,
                "official",
            ),
        ),
        required_scope="TR",
        max_age_days=365,
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        verifier,
    )

    assert result.status == FactualStatus.UNVERIFIED
    assert result.verified is False
    price_claim = next(item for item in result.claims if item.claim.value == "4.800")
    assert price_claim.status == FactualStatus.UNVERIFIED

def test_untrusted_authority_does_not_verify_claim():
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/blog",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                True,
                "blog",
            ),
            SourceRecord(
                "https://example.com/stock",
                "şu anda satışta",
                "TR",
                date.today(),
                True,
                "official",
            ),
        ),
        required_scope="TR",
        allowed_authorities=("official",),
    )
    result = EvidenceSemantics().assess(
        "655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        verifier,
    )

    assert result.status == FactualStatus.UNVERIFIED
    assert result.verified is False
    price_claim = next(item for item in result.claims if item.claim.value == "4.800")
    assert price_claim.status == FactualStatus.UNVERIFIED
