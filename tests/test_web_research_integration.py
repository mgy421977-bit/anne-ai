from anne.safety.policy import ToolPolicy
from anne.learning.web_research import WebResearcher


def test_web_research_is_allowlisted_as_read_only() -> None:
    decision = ToolPolicy().authorize("web_research", {"query": "BESS nedir?"})
    assert decision.allowed
    assert decision.side_effect is False
    assert decision.reversible is True
    assert decision.risk == 0.10
    assert decision.human_review_required is False


def test_web_research_rejects_empty_query() -> None:
    policy = ToolPolicy()
    assert policy.authorize("web_research", {"query": ""}).allowed


def test_web_research_output_is_provenance_bearing(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            from anne.learning.evidence import EvidenceItem
            return [
                EvidenceItem(
                    source="test-source",
                    claim=f"Evidence for {query}",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    researcher = WebResearcher()
    monkeypatch.setattr(researcher, "research", FakeResearcher().research)
    evidence = researcher.research("test query")
    assert evidence[0].provenance.startswith("https://")
    assert evidence[0].confidence == 0.8
