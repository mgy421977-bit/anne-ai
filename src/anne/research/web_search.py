"""Provider-neutral web research boundary for ANNE.

The search provider is deliberately injected. ANNE does not depend on Gemini,
OpenRouter, or another model provider to perform research. A provider may be
backed by a native web-search capability, a self-hosted gateway, or another
approved retrieval system.

Search results are evidence *candidates*, not verified facts. The runner never
promotes a snippet into a VERIFIED claim on its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence
from uuid import uuid4


@dataclass(frozen=True)
class WebSearchRequest:
    query: str
    max_results: int = 10
    recency_days: int | None = None
    domains: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.query.strip():
            raise ValueError("query is required")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results must be between 1 and 100")
        if self.recency_days is not None and self.recency_days < 0:
            raise ValueError("recency_days cannot be negative")


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""
    published_at: str | None = None
    source_domain: str = ""

    def validate(self) -> None:
        if not self.title.strip() or not self.url.strip():
            raise ValueError("title and url are required")


class WebSearchProvider(Protocol):
    """Minimal retrieval contract implemented by the runtime/tool gateway."""

    def search(self, request: WebSearchRequest) -> Sequence[WebSearchResult]:
        ...


@dataclass(frozen=True)
class WebResearchMission:
    """A bounded MITOS research task using web search only."""

    objective: str
    scope: str
    max_searches: int = 5
    max_results_per_search: int = 10
    mission_id: str = field(default_factory=lambda: f"web_{uuid4().hex[:12]}")

    def validate(self) -> None:
        if not self.objective.strip() or not self.scope.strip():
            raise ValueError("objective and scope are required")
        if self.max_searches < 1 or self.max_results_per_search < 1:
            raise ValueError("research budgets must be positive")


@dataclass(frozen=True)
class WebResearchReport:
    mission_id: str
    searches: tuple[WebSearchRequest, ...]
    results: tuple[WebSearchResult, ...]
    evidence_status: str = "candidate"
    verification_status: str = "UNVERIFIED"
    notes: tuple[str, ...] = ()


class WebResearchRunner:
    """Execute bounded web retrieval without inventing or verifying claims."""

    def __init__(self, provider: WebSearchProvider) -> None:
        self.provider = provider

    def run(
        self,
        mission: WebResearchMission,
        queries: Sequence[str],
        *,
        recency_days: int | None = None,
        domains: Sequence[str] = (),
    ) -> WebResearchReport:
        mission.validate()
        normalized = [q.strip() for q in queries if q.strip()]
        if not normalized:
            raise ValueError("at least one search query is required")
        if len(normalized) > mission.max_searches:
            raise ValueError("search budget exceeded")

        requests: list[WebSearchRequest] = []
        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()

        for query in normalized:
            request = WebSearchRequest(
                query=query,
                max_results=mission.max_results_per_search,
                recency_days=recency_days,
                domains=tuple(domains),
            )
            request.validate()
            requests.append(request)
            for result in self.provider.search(request):
                result.validate()
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    results.append(result)

        return WebResearchReport(
            mission_id=mission.mission_id,
            searches=tuple(requests),
            results=tuple(results),
            evidence_status="candidate" if results else "missing",
            verification_status="UNVERIFIED",
            notes=(
                "Search results are candidate evidence only.",
                "ANNE verification is required before a result may become authoritative.",
            ),
        )
