from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.derived_research_planner import DerivedResearchPlanner
from anne.learning.evidence import EvidenceItem


class FakeResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source="source-a",
                claim=query,
                kind="web",
                provenance="https://alpha.example/a",
                confidence=0.8,
                passage=query,
            ),
        ]


def test_derived_research_verification_fixture_is_bounded() -> None:
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim="bounded claim",
        source_inference_claim="bounded claim",
        status="PROPOSED",
        research_question="bounded claim",
    )
    plan = DerivedResearchPlanner(max_hypotheses=1, max_queries=1).create_plan((hypothesis,))
    assert plan is not None
    result = DerivedResearchExecutor(researcher=FakeResearcher()).execute(plan)
    assert result.queries_used == 1
    assert result.sources_used == 1
