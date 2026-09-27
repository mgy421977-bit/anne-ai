from anne.learning.evidence import EvidenceItem, SupportStatus
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def _evidence(claim: str, support: str) -> EvidenceItem:
    return EvidenceItem(
        source="test-source",
        claim=claim,
        kind="web",
        provenance="https://example.test/source",
        confidence=0.9,
        passage=claim,
        support=support,
    )


def test_loop_initializes_plan_hypotheses_and_decision() -> None:
    state = ResearchCognitiveLoop().initialize("Question")
    assert state.plan.main_question == "Question"
    assert len(state.hypotheses) == 3
    assert state.decision.action == "RESEARCH"
    assert state.decision.research_allowed is True


def test_loop_proceeds_when_primary_hypothesis_is_supported() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    evidence = [_evidence(state.hypotheses[0].claim, SupportStatus.SUPPORTS.value)]
    state = loop.initialize("Question", evidence=evidence)
    assert state.decision.action == "PROCEED"
    assert state.decision.research_allowed is False


def test_loop_preserves_uncertainty_and_requests_research() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    evidence = [
        _evidence(state.hypotheses[0].claim, SupportStatus.SUPPORTS.value),
        _evidence(state.hypotheses[0].claim, SupportStatus.CONTRADICTS.value),
    ]
    state = loop.initialize("Question", evidence=evidence)
    assert state.decision.action == "RESEARCH"
    assert state.critic.unresolved_hypotheses == ("H1",)
    assert loop.next_research_questions(state) == ("Question",)


def test_loop_stops_at_research_budget() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question", queries_used=8)
    assert state.decision.action == "STOP"
    assert state.decision.research_allowed is False
