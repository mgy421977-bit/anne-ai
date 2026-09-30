from anne.language.evidence import LanguageEvidence, LanguageLookupResult
from anne.language.verification import (
    LanguageEvidenceVerifier,
    LanguageVerificationStatus,
)


def _result(provider: str, source: str, meaning: str):
    return LanguageLookupResult(
        provider=provider,
        query="örnek",
        evidence=(
            LanguageEvidence(
                query="örnek",
                meaning=meaning,
                source_ref=source,
            ),
        ),
    )


def test_two_independent_sources_corroborate_without_authority():
    result = LanguageEvidenceVerifier().verify(
        " örnek ",
        (
            _result("bitigci", "https://bitigci.shakalin.net/madde/ornek", "bir örnek"),
            _result("tdk", "https://sozluk.gov.tr/ornek", "bir örnek"),
        ),
    )

    assert result.status is LanguageVerificationStatus.CORROBORATED
    assert len(result.independent_sources) == 2
    assert result.authoritative is False
    assert result.as_dict()["authoritative"] is False


def test_one_source_is_insufficient():
    result = LanguageEvidenceVerifier().verify(
        "örnek",
        (_result("bitigci", "https://bitigci.shakalin.net/madde/ornek", "bir örnek"),),
    )

    assert result.status is LanguageVerificationStatus.INSUFFICIENT


def test_same_provider_family_is_not_independent():
    result = LanguageEvidenceVerifier().verify(
        "örnek",
        (
            _result("bitigci", "https://bitigci.shakalin.net/a", "bir örnek"),
            _result("bitigci", "https://bitigci.shakalin.net/b", "bir örnek"),
        ),
    )

    assert result.status is LanguageVerificationStatus.INSUFFICIENT


def test_different_meanings_are_divergent_not_refuted():
    result = LanguageEvidenceVerifier().verify(
        "örnek",
        (
            _result("bitigci", "https://bitigci.shakalin.net/a", "bir örnek"),
            _result("tdk", "https://sozluk.gov.tr/a", "numune"),
        ),
    )

    assert result.status is LanguageVerificationStatus.DIVERGENT
    assert result.authoritative is False
