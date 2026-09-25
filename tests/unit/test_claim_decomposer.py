from anne.core.claim_decomposer import ClaimDecomposer


def test_decomposes_compound_price_claim():
    result = ClaimDecomposer().decompose(
        "655 W panel Türkiye'de 4.800 TL ve şu anda satışta"
    )
    assert result.complete
    assert len(result.claims) >= 2
    assert any(c.value == "4.800" for c in result.claims)
    assert any("market:TR" in c.qualifiers for c in result.claims)
    assert any("availability:current" in c.qualifiers for c in result.claims)


def test_empty_claim_is_incomplete():
    assert ClaimDecomposer().decompose("").complete is False
