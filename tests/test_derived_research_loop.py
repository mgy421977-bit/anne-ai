from anne.learning.evidence import EvidenceItem
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def test_loop_exposes_bounded_plan_for_derived_hypotheses() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    assert state.derived_hypotheses == ()
    assert state.derived_research_plan is None

    # The planner remains empty until an explicit joint inference is produced;
    # this test protects the no-invention boundary.
    evidence = EvidenceItem(
        source="source",
        claim=state.hypotheses[0].claim,
        kind="web",
        provenance="https://source.example/item",
        confidence=0.9,
        passage=state.hypotheses[0].claim,
    )
    refreshed = loop.initialize("Question", evidence=(evidence,))
    assert refreshed.derived_hypotheses == ()
    assert refreshed.derived_research_plan is None


from dataclasses import replace

from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.derived_research_planner import DerivedResearchPlanner


class FakeResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source="fresh-source-a",
                claim=f"fresh evidence for {query}",
                kind="web",
                provenance="https://fresh.example/a",
                confidence=0.8,
                passage="fresh passage",
            ),
            EvidenceItem(
                source="fresh-source-b",
                claim=f"fresh evidence for {query}",
                kind="web",
                provenance="https://fresh.example/b",
                confidence=0.8,
                passage="fresh passage",
            ),
        ]


def test_loop_executes_only_the_explicit_derived_plan() -> None:
    loop = ResearchCognitiveLoop()
    initial = loop.initialize("Question")
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim="derived claim",
        source_inference_claim="derived claim",
        status="PROPOSED",
        research_question="Independently test derived claim",
    )
    plan = DerivedResearchPlanner(max_hypotheses=1, max_queries=1).create_plan((hypothesis,))
    assert plan is not None
    state = replace(initial, derived_research_plan=plan)

    result = loop.execute_derived_research(
        state,
        executor=DerivedResearchExecutor(researcher=FakeResearcher()),
    )

    assert result is not None
    assert result.plan_question == "Independently test 1 derived hypothesis(es)"
    assert result.queries_used == 1
    assert result.sources_used == 2


def test_loop_reassesses_derived_evidence_through_normal_pipeline() -> None:
    loop = ResearchCognitiveLoop()
    initial = loop.initialize("Question")
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim="derived claim",
        source_inference_claim="derived claim",
        status="PROPOSED",
        research_question="Independently test derived claim",
    )
    plan = DerivedResearchPlanner(max_hypotheses=1, max_queries=1).create_plan((hypothesis,))
    assert plan is not None
    state = replace(initial, derived_research_plan=plan)

    refreshed = loop.reassess_after_derived_research(
        state,
        executor=DerivedResearchExecutor(researcher=FakeResearcher()),
    )

    assert refreshed.derived_research_result is not None
    assert refreshed.derived_research_result.sources_used == 2
    assert len(refreshed.evidence_ledger.as_dict()["entries"]) == 2
