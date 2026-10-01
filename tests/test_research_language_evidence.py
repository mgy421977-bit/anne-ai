from anne.language.bitigci import BitigciProvider
from anne.language.service import TurkishLanguageEvidenceService
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def test_research_loop_records_language_check_without_promoting_evidence():
    def resolver(query: str):
        return {
            "meaning": "belirsiz eylem ifadesi",
            "source_ref": "bitigci:test/bunu-yap",
            "examples": ("Bunu yapabilir misin?",),
        }

    service = TurkishLanguageEvidenceService(
        provider=BitigciProvider(resolver=resolver)
    )
    state = ResearchCognitiveLoop(language_service=service).initialize("Bunu yap")

    assert state.language_check is not None
    assert state.language_check.decision.should_lookup is True
    assert len(state.language_check.evidence) == 1
    assert state.language_check.evidence[0].support == "unclear"
    assert state.language_check.evidence[0].source == "bitigci"
    assert any(
        entry["source"] == "bitigci"
        for entry in state.evidence_ledger.as_dict()["entries"]
    )


def test_research_loop_does_not_call_language_provider_for_low_ambiguity():
    calls: list[str] = []

    def resolver(query: str):
        calls.append(query)
        return {"meaning": "unused", "source_ref": "bitigci:test"}

    service = TurkishLanguageEvidenceService(
        provider=BitigciProvider(resolver=resolver)
    )
    state = ResearchCognitiveLoop(language_service=service).initialize("Bu nedir?")

    assert state.language_check is not None
    assert state.language_check.decision.should_lookup is False
    assert state.language_check.evidence == ()
    assert calls == []


def test_research_loop_without_language_service_preserves_existing_path():
    state = ResearchCognitiveLoop().initialize("Bu nedir?")

    assert state.language_check is None
