from __future__ import annotations

import pytest

from anne.mythos.agent_swarm import AgentRole
from anne.mythos.web_research import MitosWebResearcher
from anne.tools.web_research import PublicWebResearchTool, _SearchParser


def test_search_parser_extracts_public_result_links() -> None:
    parser = _SearchParser()
    parser.feed(
        """
        <a class="result__a" href="https://example.com/panel">655 W Panel</a>
        <div class="result__snippet">Panel fiyatı</div>
        """
    )
    assert len(parser.results) == 1
    assert parser.results[0].url == "https://example.com/panel"
    assert parser.results[0].title == "655 W Panel"


def test_private_network_targets_are_blocked() -> None:
    with pytest.raises(ValueError, match="Private"):
        PublicWebResearchTool._assert_public_url("http://127.0.0.1:8080/")


class FakeWebTool:
    def research(self, query: str, *, max_results: int, fetch_pages: int) -> dict:
        return {
            "query": query,
            "pages": [
                {
                    "source": "https://example.com/source",
                    "final_url": "https://example.com/source",
                    "title": "Example source",
                    "snippet": f"Evidence for {query}",
                    "text": "source text",
                }
            ],
        }


def test_mitos_returns_unverified_evidence_package() -> None:
    researcher = MitosWebResearcher(
        tool=FakeWebTool(),  # type: ignore[arg-type]
        search_budget=2,
        max_results_per_query=2,
        fetch_pages_per_query=1,
    )
    result = researcher.research(
        "655 W güneş paneli fiyatı",
        scope="Türkiye",
        queries=["655 W güneş paneli fiyatı Türkiye"],
        role=AgentRole.ECONOMICS,
    )
    assert result.tool_calls == 1
    assert len(result.packages) == 1
    package = result.packages[0]
    assert package.role == AgentRole.ECONOMICS
    assert package.findings[0].evidence_kind == "WEB_SOURCE"
    assert package.findings[0].confidence == 0.20
    assert "unverified" in package.findings[0].uncertainty
