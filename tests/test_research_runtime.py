from __future__ import annotations

from anne.agent.runtime import AnneAgent
from anne.learning.research_planner import ResearchPlanner


def test_agent_creates_bounded_research_plan() -> None:
    agent = object.__new__(AnneAgent)
    agent.research_planner = ResearchPlanner(max_subquestions=3, max_queries=6)
    plan = agent._create_research_plan("What is the capital of France?")
    assert plan.main_question == "What is the capital of France?"
    assert len(plan.subquestions) == 3
    assert plan.query_budget == 6
    assert plan.stop_conditions.max_queries == 6


def test_agent_exposes_bounded_research_trace_from_workspace() -> None:
    agent = object.__new__(AnneAgent)
    agent.workspace = type(
        "Workspace",
        (),
        {
            "tool_results": [
                {
                    "name": "web_research",
                    "ok": True,
                    "result": {
                        "query": "Question",
                        "decision_synthesis": {
                            "status": "INSUFFICIENT_EVIDENCE",
                            "supported_hypotheses": [],
                            "unresolved_hypotheses": ["H1"],
                            "rejected_hypotheses": [],
                            "reason": "No hypothesis has decisive supporting evidence.",
                            "is_ambiguous": True,
                        },
                        "cognitive_loop": {
                            "action": "RESEARCH",
                            "reason": "Unresolved hypothesis remains.",
                        },
                        "verification": {
                            "status": "UNVERIFIED",
                            "sources": [],
                        },
                        "provenance": {"nodes": [], "edges": []},
                        "evidence_ledger": {"entries": []},
                        "reevaluation": {"action": "STOP"},
                    },
                }
            ]
        },
    )()
    trace = agent._research_trace()
    assert trace["query"] == "Question"
    assert trace["decision_synthesis"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert trace["cognitive_loop"]["action"] == "RESEARCH"
    assert trace["verification"]["status"] == "UNVERIFIED"
    assert trace["provenance"] == {"nodes": [], "edges": []}
    assert trace["evidence_ledger"] == {"entries": []}
    assert trace["reevaluation"] == {"action": "STOP"}


def test_agent_research_trace_is_empty_without_web_research() -> None:
    agent = object.__new__(AnneAgent)
    agent.workspace = type("Workspace", (), {"tool_results": []})()
    assert agent._research_trace() == {}


def test_web_research_produces_live_provenance_and_evidence_ledger() -> None:
    from anne.learning.evidence import EvidenceItem

    class FakeResearcher:
        def research(self, query: str) -> list[EvidenceItem]:
            return [
                EvidenceItem(
                    source="https://example.com/source-a",
                    claim=query,
                    kind="web",
                    provenance="example.com",
                    confidence=0.9,
                    passage=query,
                    support="supports",
                ),
                EvidenceItem(
                    source="https://example.org/source-b",
                    claim=query,
                    kind="web",
                    provenance="example.org",
                    confidence=0.8,
                    passage=query,
                    support="supports",
                ),
            ]

    agent = object.__new__(AnneAgent)
    agent.research_planner = ResearchPlanner(max_subquestions=3, max_queries=1)
    agent.web_researcher = FakeResearcher()
    agent.response_verifier = None

    result = agent._web_research("A bounded research question")

    assert result["ok"] is True
    assert len(result["evidence_ledger"]["entries"]) == 2
    assert len(result["provenance"]["nodes"]) >= 4
    assert any(
        node["kind"] == "evidence" for node in result["provenance"]["nodes"]
    )
    assert any(
        node["kind"] == "hypothesis" for node in result["provenance"]["nodes"]
    )
    assert any(
        node["kind"] == "decision_synthesis"
        for node in result["provenance"]["nodes"]
    )
    assert result["reevaluation"]["action"] == "NOT_TRIGGERED"
