from anne.core.verification import FactualStatus
from anne.research.price_intelligence import PriceObservation, PriceResearchRequest, PriceResearchRunner
from anne.research.web_search import WebSearchResult

class FakeSearchProvider:
    def search(self, request):
        return [WebSearchResult("Supplier product page", "https://example.com/product", "Product price", source_domain="example.com")]

class FakeExtractor:
    def extract(self, request, results):
        return [PriceObservation(request.item, 1000, request.currency, request.unit, results[0].url, results[0].title, brand=request.brand, model=request.model, evidence_text="price shown", extraction_method="test")]

def test_price_research_builds_source_backed_observation():
    runner = PriceResearchRunner(FakeSearchProvider(), FakeExtractor())
    request = PriceResearchRequest("100 kW inverter", brand="Huawei", model="X")
    observations = runner.research(request)
    assert len(observations) == 1
    assert observations[0].source_url == "https://example.com/product"

def test_matching_single_observation_is_verified_but_still_human_boundary():
    request = PriceResearchRequest("100 kW inverter", currency="USD")
    observation = PriceObservation(request.item, 4000, "USD", "adet", "https://example.com/product", "Product page")
    result = PriceResearchRunner.verify(request, [observation])
    assert result.status == FactualStatus.VERIFIED
    assert result.requires_human is True

def test_disagreement_is_conflicting_not_averaged():
    request = PriceResearchRequest("100 kW inverter", currency="USD")
    observations = [
        PriceObservation(request.item, 4000, "USD", "adet", "https://a.example", "A"),
        PriceObservation(request.item, 4500, "USD", "adet", "https://b.example", "B"),
    ]
    result = PriceResearchRunner.verify(request, observations)
    assert result.status == FactualStatus.CONFLICTING
    assert result.requires_human is True

def test_missing_source_never_becomes_verified():
    request = PriceResearchRequest("100 kW inverter", currency="USD")
    observation = PriceObservation(request.item, 4000, "USD", "adet", "", "")
    try:
        PriceResearchRunner.verify(request, [observation])
    except ValueError:
        pass
    else:
        raise AssertionError("source-less observation must fail")
