from anne.learning.web_providers import (
    AgentReachProvider,
    CommandResearchProvider,
    PatchrightEnhancedProvider,
    ProviderLimits,
    ResearchProviderRegistry,
)


def test_command_provider_fails_closed_without_configuration() -> None:
    provider = AgentReachProvider()
    assert provider.research("anything") == ()


def test_patchright_provider_fails_closed_without_configuration() -> None:
    provider = PatchrightEnhancedProvider()
    assert provider.research("anything") == ()


def test_command_provider_parses_bounded_jsonl(monkeypatch) -> None:
    monkeypatch.setenv("ANNE_AGENT_REACH_COMMAND", "fake-research")
    provider = AgentReachProvider(limits=ProviderLimits(max_items=1))

    class Result:
        returncode = 0
        stdout = (
            '{"claim":"claim-a","provenance":"https://example.com/a",'
            '"passage":"passage-a","confidence":0.8}\n'
            '{"claim":"claim-b","provenance":"https://example.com/b"}'
        )
        stderr = ""

    def fake_run(*args, **kwargs):
        assert args[0] == ["fake-research", "question"]
        assert kwargs["shell"] is False
        return Result()

    monkeypatch.setattr("anne.learning.web_providers.subprocess.run", fake_run)
    items = provider.research("question")
    assert len(items) == 1
    assert items[0].provenance == "https://example.com/a"
    assert items[0].confidence == 0.8


def test_registry_deduplicates_across_providers() -> None:
    class Provider:
        name = "test"

        def research(self, query):
            from anne.learning.evidence import EvidenceItem

            return (
                EvidenceItem(
                    source="a",
                    claim="same",
                    kind="web",
                    provenance="https://example.com",
                    confidence=0.5,
                ),
                EvidenceItem(
                    source="b",
                    claim="different",
                    kind="web",
                    provenance="https://example.org",
                    confidence=0.5,
                ),
            )

    registry = ResearchProviderRegistry((Provider(), Provider()), max_total_items=3)
    items = registry.research("q")
    assert len(items) == 2


def test_registry_enforces_total_bound() -> None:
    class Provider:
        name = "test"

        def research(self, query):
            from anne.learning.evidence import EvidenceItem

            return tuple(
                EvidenceItem(
                    source="s",
                    claim=str(i),
                    kind="web",
                    provenance=f"https://example.com/{i}",
                    confidence=0.5,
                )
                for i in range(5)
            )

    registry = ResearchProviderRegistry((Provider(),), max_total_items=2)
    assert len(registry.research("q")) == 2

def test_web_researcher_consumes_external_registry() -> None:
    from anne.learning.web_research import WebResearcher
    from anne.learning.evidence import EvidenceItem

    class Registry:
        def __init__(self):
            self.queries = []

        def research(self, query):
            self.queries.append(query)
            return (
                EvidenceItem(
                    source="fixture",
                    claim="external observation",
                    kind="web_external",
                    provenance="https://example.com/fixture",
                    confidence=0.5,
                ),
            )

    registry = Registry()
    researcher = WebResearcher(external_registry=registry)
    researcher._query_variants = lambda query: ()
    results = researcher.research("external observation")

    assert registry.queries == ["external observation"]
    assert any(item.claim == "external observation" for item in results)
