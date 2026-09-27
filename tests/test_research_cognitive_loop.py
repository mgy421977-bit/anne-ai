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
    assert "H1" in state.critic.unresolved_hypotheses
    questions = loop.next_research_questions(state)
    assert questions[0] == "Look for credible evidence that contradicts or qualifies: Question"
    assert len(questions) == 1


def test_loop_stops_at_research_budget() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question", queries_used=8)
    assert state.decision.action == "STOP"
    assert state.decision.research_allowed is False

def test_loop_exposes_synthesis_and_provenance_re_evaluation() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    evidence = [_evidence(state.hypotheses[0].claim, SupportStatus.SUPPORTS.value)]
    state = loop.initialize("Question", evidence=evidence)

    assert state.synthesis.status.value == "SUPPORTED"
    provenance = state.evidence_ledger.provenance()
    node_ids = {node["id"] for node in provenance["nodes"]}
    assert "H1" in node_ids
    assert "SYNTHESIS" in node_ids

    evidence_id = next(
        node["id"] for node in provenance["nodes"] if node["kind"] == "evidence"
    )
    plan = state.evidence_ledger.re_evaluation_plan(evidence_id)
    assert plan.action == "RESEARCH"
    assert "H1" in plan.stale_nodes
    assert "SYNTHESIS" in plan.stale_nodes

def test_evidence_invalidation_propagates_to_hypothesis_and_synthesis() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    evidence = [_evidence(state.hypotheses[0].claim, SupportStatus.SUPPORTS.value)]
    state = loop.initialize("Question", evidence=evidence)

    evidence_id = next(
        node["id"] for node in state.evidence_ledger.provenance()["nodes"]
        if node["kind"] == "evidence"
    )

    affected = state.evidence_ledger.invalidate_evidence(evidence_id)
    assert affected == (evidence_id, "H1", "SYNTHESIS")
    assert state.evidence_ledger.status(evidence_id).value == "invalidated"
    assert state.evidence_ledger.status("H1").value == "stale"
    assert state.evidence_ledger.status("SYNTHESIS").value == "stale"

    plan = state.evidence_ledger.re_evaluation_plan(evidence_id)
    assert plan.requires_research is True
    assert plan.action == "RESEARCH"
    assert plan.stale_nodes == ("H1", "SYNTHESIS")


def test_re_evaluation_rebuilds_state_from_fresh_evidence() -> None:
    loop = ResearchCognitiveLoop()
    initial = loop.initialize("Question")
    old_evidence = _evidence(
        initial.hypotheses[0].claim,
        SupportStatus.SUPPORTS.value,
    )
    initial = loop.initialize("Question", evidence=[old_evidence])

    evidence_id = next(
        node["id"]
        for node in initial.evidence_ledger.provenance()["nodes"]
        if node["kind"] == "evidence"
    )
    plan = initial.evidence_ledger.re_evaluation_plan(evidence_id)

    fresh_evidence = _evidence(
        initial.hypotheses[0].claim,
        SupportStatus.CONTRADICTS.value,
    )
    refreshed = loop.continue_from_re_evaluation(
        plan,
        "Question",
        evidence=[fresh_evidence],
    )

    assert refreshed is not None
    assert refreshed is not initial
    assert refreshed.synthesis.status.value != initial.synthesis.status.value
    assert refreshed.decision.action == "RESEARCH"
    assert all(
        node["status"] == "active"
        for node in refreshed.evidence_ledger.provenance()["nodes"]
    )
