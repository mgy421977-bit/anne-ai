"""MITOS public-web research bridge.

MITOS owns the research mission; ANNE receives an evidence package.
No claim is promoted to FACT here. Web findings remain unverified until
ANNE's validation layer independently evaluates them.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from anne.tools.web_research import PublicWebResearchTool

from .agent_swarm import AgentRole, EvidenceItem, EvidencePackage, ResearchAgent, ResearchMission


@dataclass(frozen=True)
class MitosResearchResult:
    objective: str
    queries: tuple[str, ...]
    packages: tuple[EvidencePackage, ...]
    tool_calls: int


class MitosWebResearcher:
    """Execute bounded public-web research and return EvidencePackage records."""

    def __init__(
        self,
        tool: PublicWebResearchTool | None = None,
        *,
        search_budget: int = 12,
        max_results_per_query: int = 6,
        fetch_pages_per_query: int = 3,
    ) -> None:
        if search_budget < 1:
            raise ValueError("search_budget must be positive")
        self.tool = tool or PublicWebResearchTool()
        self.search_budget = search_budget
        self.max_results_per_query = max_results_per_query
        self.fetch_pages_per_query = fetch_pages_per_query

    @staticmethod
    def _default_queries(objective: str, scope: str) -> list[str]:
        base = " ".join(objective.split())
        queries = [base]
        if scope.strip():
            queries.append(f"{base} {scope.strip()}")
        queries.append(f"{base} current price source")
        return list(dict.fromkeys(queries))

    def research(
        self,
        objective: str,
        *,
        scope: str = "",
        queries: list[str] | None = None,
        role: AgentRole = AgentRole.CUSTOM,
    ) -> MitosResearchResult:
        if not objective.strip():
            raise ValueError("objective is required")

        mission = ResearchMission(
            objective=objective,
            scope=scope or "public web research",
            role=role,
            mission_id=f"mission_{uuid4().hex[:12]}",
            allowed_tools=("web_search", "web_fetch"),
            search_budget=self.search_budget,
            output_schema="EvidencePackage",
        )
        agent = ResearchAgent(mission)
        agent.authorize()
        agent.start()

        selected_queries = queries or self._default_queries(objective, scope)
        selected_queries = selected_queries[: self.search_budget]
        packages: list[EvidencePackage] = []
        tool_calls = 0

        for query in selected_queries:
            data = self.tool.research(
                query,
                max_results=self.max_results_per_query,
                fetch_pages=self.fetch_pages_per_query,
            )
            tool_calls += 1
            findings: list[EvidenceItem] = []

            for page in data.get("pages", []):
                source = str(page.get("final_url") or page.get("source") or "").strip()
                if not source:
                    continue
                title = str(page.get("title") or "").strip()
                snippet = str(page.get("snippet") or "").strip()
                text = str(page.get("text") or "").strip()
                claim = title or snippet or f"Public web source found for: {query}"
                if snippet:
                    claim = f"{claim} — {snippet}"
                findings.append(
                    EvidenceItem(
                        claim=claim[:2000],
                        source=source,
                        evidence_kind="WEB_SOURCE",
                        confidence=0.20,
                        uncertainty="unverified public-web evidence",
                        provenance=f"MITOS:web_research:{query}",
                    )
                )
                if text and len(findings) >= self.fetch_pages_per_query:
                    # Keep the EvidencePackage compact; the source URL is the
                    # durable provenance anchor and ANNE may refetch when needed.
                    pass

            if not findings:
                findings.append(
                    EvidenceItem(
                        claim=f"No fetchable source was found for query: {query}",
                        source="public_web_search",
                        evidence_kind="SEARCH_GAP",
                        confidence=0.0,
                        uncertainty="no independently verified source",
                        provenance=f"MITOS:web_research:{query}",
                    )
                )

            package = EvidencePackage(
                mission_id=mission.mission_id,
                agent_id=agent.agent_id,
                role=role,
                findings=tuple(findings),
                open_questions=(
                    "ANNE must independently validate source relevance, date, scope and price.",
                ),
            )
            packages.append(agent.report(package))
            # A new package requires a new research agent under the same mission
            # contract because ResearchAgent transitions to COMPLETED after report.
            if query != selected_queries[-1]:
                agent = ResearchAgent(mission)
                agent.authorize()
                agent.start()

        return MitosResearchResult(
            objective=objective,
            queries=tuple(selected_queries),
            packages=tuple(packages),
            tool_calls=tool_calls,
        )


__all__ = ["MitosResearchResult", "MitosWebResearcher"]
