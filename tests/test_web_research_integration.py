from anne.agent.runtime import AnneAgent
from anne.learning.evidence import EvidenceItem
from anne.learning.web_research import WebResearcher
from anne.safety.policy import ToolPolicy


def test_web_research_is_allowlisted_as_read_only() -> None:
    decision = ToolPolicy().authorize("web_research", {"query": "BESS nedir?"})
    assert decision.allowed
    assert decision.side_effect is False
    assert decision.reversible is True
    assert decision.risk == 0.10
    assert decision.human_review_required is False


def test_web_research_output_is_provenance_bearing(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim=f"Evidence for {query}",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("test query")
    assert result["ok"] is True
    assert result["evidence_count"] == 1
    item = result["evidence"][0]
    assert item["provenance"] == "https://example.test/source"
    assert item["confidence"] == 0.8
    assert item["status"] == "unverified"
    assert result["independent_verification"] == "not_performed"


def test_web_research_is_exposed_to_model_tool_schema() -> None:
    names = {
        item["function"]["name"]
        for item in AnneAgent.TOOL_SCHEMAS
        if item.get("type") == "function"
    }
    assert "web_research" in names
