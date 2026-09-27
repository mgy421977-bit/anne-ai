from anne.learning.provenance_graph import (
    NodeStatus,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
)


def test_invalidation_propagates_without_deleting_history() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "source passage"))
    graph.add_node(ProvenanceNode("C1", "claim", "derived claim"))
    graph.add_node(ProvenanceNode("H1", "hypothesis", "working hypothesis"))
    graph.add_node(ProvenanceNode("A1", "answer", "derived answer"))
    graph.add_edge(ProvenanceEdge("E1", "C1"))
    graph.add_edge(ProvenanceEdge("C1", "H1"))
    graph.add_edge(ProvenanceEdge("H1", "A1"))

    affected = graph.invalidate("E1")

    assert affected == ("E1", "C1", "H1", "A1")
    assert graph.get("E1").status is NodeStatus.INVALIDATED
    assert graph.get("C1").status is NodeStatus.STALE
    assert graph.get("H1").status is NodeStatus.STALE
    assert graph.get("A1").status is NodeStatus.STALE
    assert "E1" in graph.as_dict()["nodes"][0]["id"]


def test_duplicate_edges_are_idempotent() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "source"))
    graph.add_node(ProvenanceNode("C1", "claim", "claim"))
    edge = ProvenanceEdge("E1", "C1")
    graph.add_edge(edge)
    graph.add_edge(edge)

    assert len(graph.as_dict()["edges"]) == 1


def test_missing_dependency_fails_closed() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "source"))

    try:
        graph.add_edge(ProvenanceEdge("E1", "C1"))
    except ValueError as exc:
        assert "endpoints" in str(exc)
    else:
        raise AssertionError("missing dependency endpoint must fail closed")
