from anne.research.general import GeneralResearchEngine, ResearchMission
from anne.research.web_search import WebSearchResult


class FakeSearchProvider:
    def __init__(self):
        self.requests = []

    def search(self, request):
        self.requests.append(request)
        return [
            WebSearchResult(
                title="Research source",
                url="https://example.com/source",
                snippet="candidate evidence",
                source_domain="example.com",
            )
        ]


def test_general_research_is_client_neutral_and_bounded():
    provider = FakeSearchProvider()
    engine = GeneralResearchEngine(provider)

    report = engine.research(
        ResearchMission(
            objective="research 100 kW inverter options",
            scope="Türkiye",
            questions=("compare supplier evidence", "check current market"),
            max_searches=3,
        )
    )

    assert report.objective == "research 100 kW inverter options"
    assert report.scope == "Türkiye"
    assert len(provider.requests) == 3
    assert len(report.sources) == 1
    assert report.evidence_status == "candidate"
    assert report.verification_status == "UNVERIFIED"


def test_general_research_never_claims_verification():
    provider = FakeSearchProvider()
    engine = GeneralResearchEngine(provider)

    report = engine.research(ResearchMission(objective="research something"))

    assert report.verification_status == "UNVERIFIED"
    assert any("candidate evidence" in note for note in report.notes)


def test_empty_objective_fails():
    try:
        GeneralResearchEngine(FakeSearchProvider()).research(ResearchMission(objective=""))
    except ValueError as exc:
        assert "objective" in str(exc)
    else:
        raise AssertionError("empty objective must fail")
