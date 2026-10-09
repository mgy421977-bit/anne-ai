from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.derived_research_planner import DerivedResearchPlanner
from anne.learning.evidence import EvidenceItem


class FakeResearcher:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def research(self, query: str) -> list[EvidenceItem]:
        self.queries.append(query)
        return [
            EvidenceItem(
                source="source-a",
                claim=f"evidence for {query}",
                kind="web",
                provenance=f"https://a.example/{query}",
                confidence=0.8,
                passage="passage",
            ),
            EvidenceItem(
                source="source-b",
                claim=f"evidence for {query}",
                kind="web",
                provenance=f"https://b.example/{query}",
                confidence=0.8,
                passage="passage",
            ),
            EvidenceItem(
                source="source-c",
                claim=f"evidence for {query}",
                kind="web",
                provenance=f"https://c.example/{query}",
                confidence=0.8,
                passage="passage",
            ),
        ]


def _plan(max_queries: int = 2):
    hypotheses = (
        DerivedHypothesis(
            id="DH1",
            claim="A and B imply X",
            source_inference_claim="A and B imply X",
            status="PROPOSED",
            research_question="Independently test A and B imply X",
        ),
        DerivedHypothesis(
            id="DH2",
            claim="C and D imply Y",
            source_inference_claim="C and D imply Y",
            status="PROPOSED",
            research_question="Independently test C and D imply Y",
        ),
    )
    return DerivedResearchPlanner(
        max_hypotheses=2,
        max_queries=max_queries,
    ).create_plan(hypotheses)


def test_executor_runs_only_bounded_plan_questions() -> None:
    researcher = FakeResearcher()
    result = DerivedResearchExecutor(researcher=researcher).execute(_plan())
    assert len(researcher.queries) == 1
    assert result.queries_used == 1
    assert result.sources_used == 2
    assert result.stopped_reason == "source_budget_exhausted"


def test_executor_enforces_global_source_budget() -> None:
    researcher = FakeResearcher()
    plan = _plan(max_queries=4)
    result = DerivedResearchExecutor(researcher=researcher).execute(plan)
    assert result.sources_used == 4
    assert len(result.evidence) == 4
    assert result.stopped_reason == "source_budget_exhausted"


def test_executor_does_not_verify_or_authorize_results() -> None:
    researcher = FakeResearcher()
    result = DerivedResearchExecutor(researcher=researcher).execute(_plan())
    payload = result.as_dict()
    assert "verification" not in payload
    assert "authority" not in payload
    assert "decision" not in payload
