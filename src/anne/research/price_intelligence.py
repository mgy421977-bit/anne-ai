"""Evidence-preserving product and price research for VITA integrations.

This module deliberately separates four things:
1. the item VITA needs,
2. market observations returned by a search/extraction provider,
3. ANNE's verification decision,
4. the human/commercial approval boundary.

No model output is treated as a price fact merely because it is structured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence
from uuid import uuid4

from anne.core.verification import FactualStatus
from anne.research.web_search import WebResearchMission, WebSearchResult, WebSearchProvider, WebResearchRunner


@dataclass(frozen=True)
class PriceResearchRequest:
    item: str
    product_code: str = ""
    brand: str = ""
    model: str = ""
    required_spec: str = ""
    market: str = "Türkiye"
    currency: str = "TRY"
    unit: str = "adet"
    max_searches: int = 5
    request_id: str = field(default_factory=lambda: f"price_{uuid4().hex[:12]}")

    def validate(self) -> None:
        if not self.item.strip():
            raise ValueError("item is required")
        if not self.market.strip() or not self.currency.strip() or not self.unit.strip():
            raise ValueError("market, currency and unit are required")
        if self.max_searches < 1:
            raise ValueError("max_searches must be positive")


@dataclass(frozen=True)
class PriceObservation:
    item: str
    unit_price: float
    currency: str
    unit: str
    source_url: str
    source_title: str
    source_date: str | None = None
    supplier: str = ""
    brand: str = ""
    model: str = ""
    evidence_text: str = ""
    extraction_method: str = ""

    def validate(self) -> None:
        if not self.item.strip() or self.unit_price <= 0:
            raise ValueError("item and positive unit_price are required")
        if not self.currency.strip() or not self.unit.strip():
            raise ValueError("currency and unit are required")
        if not self.source_url.strip() or not self.source_title.strip():
            raise ValueError("source URL and title are required")


class PriceExtractor(Protocol):
    """Extract observations from retrieved pages/snippets.

    Implementations may use Gemini, OpenRouter, a local model, or deterministic
    extraction. The extractor only proposes observations; ANNE still verifies.
    """

    def extract(
        self,
        request: PriceResearchRequest,
        results: Sequence[WebSearchResult],
    ) -> Sequence[PriceObservation]:
        ...


@dataclass(frozen=True)
class PriceVerification:
    status: FactualStatus
    sources: tuple[str, ...]
    reason: str
    observations: tuple[PriceObservation, ...]
    requires_human: bool


class PriceResearchRunner:
    """Bounded product/price workflow; never auto-approves commercial pricing."""

    def __init__(self, search_provider: WebSearchProvider, extractor: PriceExtractor) -> None:
        self.search = WebResearchRunner(search_provider)
        self.extractor = extractor

    @staticmethod
    def build_queries(request: PriceResearchRequest) -> tuple[str, ...]:
        identity = " ".join(
            part for part in (request.brand, request.model, request.item, request.required_spec) if part
        )
        queries = [
            f"{identity} {request.market} fiyat {request.currency}",
            f"{identity} supplier price {request.currency}",
        ]
        return tuple(dict.fromkeys(q.strip() for q in queries if q.strip()))[:request.max_searches]

    def research(self, request: PriceResearchRequest) -> tuple[PriceObservation, ...]:
        request.validate()
        mission = WebResearchMission(
            objective=f"Research market price for {request.item}",
            scope=request.market,
            max_searches=request.max_searches,
        )
        report = self.search.run(mission, self.build_queries(request))
        observations = tuple(self.extractor.extract(request, report.results))
        for observation in observations:
            observation.validate()
        return observations

    @staticmethod
    def verify(
        request: PriceResearchRequest,
        observations: Sequence[PriceObservation],
    ) -> PriceVerification:
        valid = []
        for observation in observations:
            observation.validate()
            if observation.currency.upper() == request.currency.upper() and observation.unit == request.unit:
                valid.append(observation)

        if not valid:
            return PriceVerification(
                FactualStatus.UNVERIFIED, (),
                "No source-backed observation matched the requested currency and unit.",
                tuple(observations), True,
            )

        urls = tuple(sorted({o.source_url for o in valid}))
        identities = {(o.brand.lower(), o.model.lower()) for o in valid if o.brand or o.model}
        prices = {round(o.unit_price, 6) for o in valid}

        # Multiple observations are useful evidence, but disagreement is not
        # silently averaged into a selling price.
        if len(prices) > 1 or len(identities) > 1:
            return PriceVerification(
                FactualStatus.CONFLICTING, urls,
                "Source observations disagree on price or product identity; human review required.",
                tuple(valid), True,
            )

        return PriceVerification(
            FactualStatus.VERIFIED, urls,
            "Source-backed observations agree on product identity, unit and price.",
            tuple(valid), True,
        )


__all__ = [
    "PriceResearchRequest",
    "PriceObservation",
    "PriceExtractor",
    "PriceVerification",
    "PriceResearchRunner",
]
