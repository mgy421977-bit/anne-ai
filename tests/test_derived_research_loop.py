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
