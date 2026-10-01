from anne.learning.web_providers import (
    AgentReachProvider,
    PatchrightEnhancedProvider,
    ProviderLimits,
    ScraplingProvider,
)


def test_agent_reach_probe_contract(monkeypatch) -> None:
    monkeypatch.setenv("ANNE_AGENT_REACH_COMMAND", "fake-agent-reach")
    provider = AgentReachProvider(limits=ProviderLimits(max_items=1))

    class Result:
        returncode = 0
        stdout = '{"claim":"ok","provenance":"https://example.com","confidence":0.8}\n'
        stderr = ""

    monkeypatch.setattr("anne.learning.web_providers.subprocess.run", lambda *a, **k: Result())
    items = provider.research("smoke")
    assert len(items) == 1
    assert items[0].provenance == "https://example.com"


def test_patchright_probe_contract(monkeypatch) -> None:
    monkeypatch.setenv("ANNE_PATCHRIGHT_COMMAND", "fake-patchright")
    provider = PatchrightEnhancedProvider(limits=ProviderLimits(max_items=1))

    class Result:
        returncode = 0
        stdout = '{"claim":"ok","provenance":"https://example.com","confidence":0.7}\n'
        stderr = ""

    monkeypatch.setattr("anne.learning.web_providers.subprocess.run", lambda *a, **k: Result())
    items = provider.research("smoke")
    assert len(items) == 1


def test_scrapling_probe_contract() -> None:
    def fake_fetch(url: str, **_: object) -> object:
        class Page:
            status = 200

            @staticmethod
            def get_all_text(**__: object) -> str:
                return "bounded evidence"

        return Page()

    provider = ScraplingProvider(fetch_page=fake_fetch)
    items = provider.research("https://example.com")
    assert len(items) == 1
    assert items[0].provenance == "https://example.com"
