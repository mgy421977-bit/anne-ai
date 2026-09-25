from anne.research.web_search import (
    WebResearchMission,
    WebResearchRunner,
    WebSearchRequest,
    WebSearchResult,
)


class FakeSearchProvider:
    def __init__(self):
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        return [
            WebSearchResult(
                title="Example product",
                url="https://example.com/product",
                snippet="Example price evidence",
                source_domain="example.com",
            )
        ]


def test_web_search_request_requires_query():
    request = WebSearchRequest(query="")
    try:
        request.validate()
    except ValueError as exc:
        assert "query" in str(exc)
    else:
        raise AssertionError("empty query must fail")


def test_web_research_is_bounded_and_unverified():
    provider = FakeSearchProvider()
    runner = WebResearchRunner(provider)
    report = runner.run(
        WebResearchMission("research product price", "Türkiye market", max_searches=2),
        ["product model price", "product model supplier"],
    )

    assert len(provider.requests) == 2
    assert len(report.results) == 1
    assert report.evidence_status == "candidate"
    assert report.verification_status == "UNVERIFIED"
    assert report.notes


def test_web_research_rejects_budget_overrun():
    runner = WebResearchRunner(FakeSearchProvider())
    mission = WebResearchMission("research", "scope", max_searches=1)
    try:
        runner.run(mission, ["one", "two"])
    except ValueError as exc:
        assert "budget" in str(exc)
    else:
        raise AssertionError("budget overrun must fail")
