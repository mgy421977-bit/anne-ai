from anne.language.bitigci import BitigciProvider
from anne.language.evidence import LanguageEvidenceProvider


def test_bitigci_provider_emits_non_authoritative_provenance():
    provider = BitigciProvider(
        lambda query: {
            "meaning": "Bir sözcüğün bağlama göre açıklaması.",
            "examples": ("Örnek kullanım.",),
            "context": {"register": "standard", "domain": "general"},
            "source_ref": "https://bitigci.shakalin.net/madde/ornek",
        }
    )

    assert isinstance(provider, LanguageEvidenceProvider)
    result = provider.lookup(" örnek ")
    assert result.available is True
    assert result.provider == "bitigci"
    assert result.query == "örnek"

    item = result.evidence[0]
    evidence = item.as_evidence("lang-1")
    assert evidence.provenance.source_ref.endswith("/ornek")
    assert evidence.provenance.verified is False
    assert evidence.provenance.source_type == "tool"
    assert evidence.content_hash
    assert "Örnek kullanım." in evidence.content


def test_bitigci_provider_fails_closed_without_resolver():
    result = BitigciProvider().lookup("bağlam")

    assert result.available is False
    assert result.evidence == ()
    assert result.warnings == ("No approved Bitigçi resolver configured.",)


def test_bitigci_provider_does_not_turn_missing_meaning_into_evidence():
    result = BitigciProvider(lambda _: {"examples": ("Tanık.",)}).lookup("kelime")

    assert result.available is False
    assert result.evidence == ()
    assert "no lexical meaning" in result.warnings[0].lower()


def test_provider_failure_is_bounded():
    def failing(_: str):
        raise RuntimeError("network")

    result = BitigciProvider(failing).lookup("kelime")

    assert result.available is False
    assert result.evidence == ()
    assert result.warnings == ("Bitigçi resolver failed: RuntimeError",)
