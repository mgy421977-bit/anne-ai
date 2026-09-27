from anne.learning.provenance_graph import NodeStatus, ProvenanceGraph, ProvenanceNode
from anne.learning.reevaluation import ReEvaluationPlanner
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def test_re_evaluation_plan_reenters_research_loop() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "old source"))
    graph.add_node(ProvenanceNode("C1", "claim", "claim"))
    from anne.learning.provenance_graph import ProvenanceEdge
    graph.add_edge(ProvenanceEdge("E1", "C1", "supports"))

    plan = ReEvaluationPlanner().create_plan(graph, "E1")
    state = ResearchCognitiveLoop().continue_from_re_evaluation(plan, "claim")

    assert state is not None
    assert state.plan.main_question == "claim"


def test_stop_plan_does_not_reenter_research_loop() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "isolated"))
    plan = ReEvaluationPlanner().create_plan(graph, "E1")

    assert ResearchCognitiveLoop().continue_from_re_evaluation(plan, "claim") is None
    assert graph.get("E1").status is NodeStatus.INVALIDATED
