from anne.core.intent import IntentClassifier
from anne.language.bitigci import BitigciProvider
from anne.language.service import TurkishLanguageEvidenceService


def test_low_ambiguity_does_not_call_provider():
    calls: list[str] = []

    def resolver(query: str):
        calls.append(query)
        return {"meaning": "unused", "source_ref": "bitigci:test"}

    intent = IntentClassifier().classify("Bu nedir?")
    result = TurkishLanguageEvidenceService(
        provider=BitigciProvider(resolver=resolver)
    ).check("Bu nedir?", intent)

    assert result.decision.should_lookup is False
    assert result.lookup is None
    assert result.evidence == ()
    assert calls == []


def test_high_ambiguity_routes_provider_into_ledger_observations():
    calls: list[str] = []

    def resolver(query: str):
        calls.append(query)
        return {
            "meaning": "belirsiz eylem ifadesi",
            "source_ref": "bitigci:test/bunu-yap",
            "examples": ("Bunu yapabilir misin?",),
            "context": {"register": "günlük"},
        }

    intent = IntentClassifier().classify("Bunu yap")
    result = TurkishLanguageEvidenceService(
        provider=BitigciProvider(resolver=resolver)
    ).check("Bunu yap", intent)

    assert result.decision.should_lookup is True
    assert result.lookup is not None
    assert result.available is True
    assert calls == ["Bunu yap"]
    assert result.evidence[0].source == "bitigci"
    assert result.evidence[0].support == "unclear"
    assert result.evidence[0].provenance == "bitigci:test/bunu-yap"
    assert "register=günlük" in result.evidence[0].passage


def test_provider_failure_fails_closed_without_evidence():
    def resolver(_: str):
        raise RuntimeError("provider unavailable")

    intent = IntentClassifier().classify("Bunu yap")
    result = TurkishLanguageEvidenceService(
        provider=BitigciProvider(resolver=resolver)
    ).check("Bunu yap", intent)

    assert result.lookup is not None
    assert result.evidence == ()
    assert result.available is False
    assert result.lookup.warnings == ("Bitigçi resolver failed: RuntimeError",)


def test_missing_provider_is_bounded_and_non_authoritative():
    intent = IntentClassifier().classify("Bunu yap")
    result = TurkishLanguageEvidenceService().check("Bunu yap", intent)

    assert result.decision.should_lookup is True
    assert result.evidence == ()
    assert result.lookup is not None
    assert result.lookup.provider == "unconfigured"
    assert result.lookup.warnings == ("No language evidence provider configured.",)
