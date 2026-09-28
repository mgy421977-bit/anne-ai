from anne.core.trace import CycleTrace\nfrom anne.learning.experience_learning import Experience
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def test_completed_trace_can_route_research_loop_to_fresh_research() -> None:
    trace = CycleTrace(
        cycle_id="cycle-gap",
        status="BOUNDED",
        stop_reason="evidence_gap",
        verification={"status": "UNVERIFIED"},
        decision={"status": "INSUFFICIENT_EVIDENCE"},
    )
    state = ResearchCognitiveLoop().initialize(
        "A question requiring evidence",
        completed_trace=trace,
        strategy="answer_directly",
    )
    assert state.adaptive_learning is not None
    assert state.adaptive_learning.information_gap.present is True
    assert state.decision.action == "RESEARCH"
    assert state.adaptive_learning.strategy.strategy == "seek_fresh_independent_evidence"


def test_completed_trace_is_not_used_as_authority() -> None:
    trace = CycleTrace(
        cycle_id="cycle-safe",
        status="BOUNDED",
        stop_reason="execution_risk",
    )
    state = ResearchCognitiveLoop().initialize(
        "A question",
        completed_trace=trace,
        strategy="execute",
    )
    assert state.adaptive_learning is not None
    assert state.adaptive_learning.strategy.action == "ABSTAIN"
    assert state.adaptive_learning.strategy.strategy == "require_authority_review"
