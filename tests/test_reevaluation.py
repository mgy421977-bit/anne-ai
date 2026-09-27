from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceGraph, ProvenanceNode
from anne.learning.reevaluation import ReEvaluationPlanner


def _graph() -> ProvenanceGraph:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "source"))
    graph.add_node(ProvenanceNode("C1", "claim", "claim"))
    graph.add_node(ProvenanceNode("H1", "hypothesis", "hypothesis"))
    graph.add_node(ProvenanceNode("A1", "answer", "answer"))
    graph.add_edge(ProvenanceEdge("E1", "C1", "supports"))
    graph.add_edge(ProvenanceEdge("C1", "H1", "derived_from"))
    graph.add_edge(ProvenanceEdge("H1", "A1", "derived_from"))
    return graph


def test_invalidated_dependency_creates_research_plan() -> None:
    plan = ReEvaluationPlanner().create_plan(_graph(), "E1")

    assert plan.action == "RESEARCH"
    assert plan.requires_research is True
    assert plan.stale_nodes == ("C1", "H1", "A1")


def test_isolated_invalidated_dependency_stops() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "source"))

    plan = ReEvaluationPlanner().create_plan(graph, "E1")

    assert plan.action == "STOP"
    assert plan.requires_research is False
    assert plan.stale_nodes == ()
