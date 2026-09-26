from anne.learning.critic_loop import CriticLoopController
from anne.learning.hypothesis import HypothesisEngine, HypothesisStatus, HypothesisCritic


def _unresolved():
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=1)
    return HypothesisCritic().assess(
        hypotheses,
        [("H1", "SUPPORTS"), ("H1", "CONTRADICTS")],
    )


def test_critic_loop_requests_research_when_budget_exists() -> None:
    decision = CriticLoopController().decide(
        _unresolved(), queries_used=1, max_queries=5
    )
    assert decision.action == "RESEARCH"
    assert decision.research_allowed is True


def test_critic_loop_stops_when_query_budget_exhausted() -> None:
    decision = CriticLoopController().decide(
        _unresolved(), queries_used=5, max_queries=5
    )
    assert decision.action == "STOP"
    assert decision.research_allowed is False


def test_critic_loop_proceeds_when_no_uncertainty_remains() -> None:
    hypotheses = HypothesisEngine().generate("Question", max_hypotheses=1)
    result = HypothesisCritic().assess(hypotheses, [("H1", "SUPPORTS")])
    decision = CriticLoopController().decide(
        result, queries_used=5, max_queries=5
    )
    assert decision.action == "PROCEED"


def test_critic_loop_stops_when_source_budget_exhausted() -> None:
    decision = CriticLoopController().decide(
        _unresolved(), queries_used=1, max_queries=5,
        sources_used=12, max_sources=12,
    )
    assert decision.action == "STOP"
