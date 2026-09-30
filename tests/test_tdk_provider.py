from anne.language.evidence import LanguageEvidenceProvider
from anne.language.tdk import TdkProvider


def test_tdk_provider_emits_non_authoritative_provenance():
    provider = TdkProvider(
        lambda query: {
            "meaning": "Bir sözcüğün sözlük anlamı.",
            "examples": ("Örnek kullanım.",),
            "source_ref": "https://sozluk.gov.tr/kelime/ornek",
        }
    )

    assert isinstance(provider, LanguageEvidenceProvider)
    result = provider.lookup(" örnek ")
    assert result.available is True
    assert result.provider == "tdk"
    assert result.query == "örnek"
    item = result.evidence[0]
    assert item.source_ref.endswith("/ornek")
    assert item.source_type == "official_dictionary"
    assert item.content_hash


def test_tdk_provider_fails_closed_without_resolver():
    result = TdkProvider().lookup("kelime")

    assert result.available is False
    assert result.evidence == ()
    assert result.warnings == ("No approved TDK resolver configured.",)


def test_tdk_provider_requires_meaning_and_provenance():
    result = TdkProvider(
        lambda _: {"examples": ("Tanık.",)}
    ).lookup("kelime")

    assert result.available is False
    assert "lexical meaning" in result.warnings[0]

    result = TdkProvider(
        lambda _: {"meaning": "Anlam var ama kaynak yok."}
    ).lookup("kelime")

    assert result.available is False
    assert "source provenance" in result.warnings[0]


def test_tdk_provider_failure_is_bounded():
    def failing(_: str):
        raise RuntimeError("network")

    result = TdkProvider(failing).lookup("kelime")

    assert result.available is False
    assert result.evidence == ()
    assert result.warnings == ("TDK resolver failed: RuntimeError",)
