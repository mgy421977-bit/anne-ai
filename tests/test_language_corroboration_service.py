from anne.core.intent import IntentClassifier, IntentKind
from anne.language.bitigci import BitigciProvider
from anne.language.corroboration import TurkishLanguageCorroborationService
from anne.language.tdk import TdkProvider
from anne.language.verification import LanguageVerificationStatus


def test_corroboration_requires_two_explicit_providers():
    intent = IntentClassifier().classify("Bunu yap")
    service = TurkishLanguageCorroborationService(
        providers=(
            BitigciProvider(lambda _: {
                "meaning": "belirsiz eylem ifadesi",
                "source_ref": "https://bitigci.shakalin.net/madde/bunu-yap",
            }),
        )
    )

    result = service.check("Bunu yap", intent)

    assert result.verification is not None
    assert result.verification.status is LanguageVerificationStatus.INSUFFICIENT
    assert result.lookups == ()


def test_independent_language_providers_can_corrobate():
    intent = IntentClassifier().classify("Bunu yap")
    service = TurkishLanguageCorroborationService(
        providers=(
            BitigciProvider(lambda _: {
                "meaning": "belirsiz eylem ifadesi",
                "source_ref": "https://bitigci.shakalin.net/madde/bunu-yap",
            }),
            TdkProvider(lambda _: {
                "meaning": "belirsiz eylem ifadesi",
                "source_ref": "https://sozluk.gov.tr/madde/bunu-yap",
            }),
        )
    )

    result = service.check("Bunu yap", intent)

    assert result.verification is not None
    assert result.verification.status is LanguageVerificationStatus.CORROBORATED
    assert result.verification.authoritative is False
    assert len(result.verification.independent_sources) == 2


def test_low_ambiguity_does_not_call_language_providers():
    calls = {"bitigci": 0, "tdk": 0}

    def bitigci(_):
        calls["bitigci"] += 1
        return {"meaning": "x", "source_ref": "https://bitigci.shakalin.net/x"}

    def tdk(_):
        calls["tdk"] += 1
        return {"meaning": "x", "source_ref": "https://sozluk.gov.tr/x"}

    intent = IntentClassifier().classify("Bu nedir?")
    result = TurkishLanguageCorroborationService(
        providers=(BitigciProvider(bitigci), TdkProvider(tdk))
    ).check("Bu nedir?", intent)

    assert result.verification is None
    assert calls == {"bitigci": 0, "tdk": 0}
