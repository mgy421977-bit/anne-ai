from anne.learning.provenance_graph import (
    NodeStatus,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
)
from anne.learning.reevaluation_executor import ReEvaluationExecutor


def test_rebuild_creates_explicit_replacement_and_preserves_stale_history() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "old source"))
    graph.add_node(ProvenanceNode("C1", "claim", "old claim"))
    graph.add_edge(ProvenanceEdge("E1", "C1", "supports"))
    graph.invalidate("E1")

    graph.add_node(ProvenanceNode("E2", "evidence", "fresh source"))

    result = ReEvaluationExecutor().rebuild(
        graph,
        stale_node="C1",
        replacement_node="C2",
        replacement_kind="claim",
        replacement_content="re-evaluated claim",
        fresh_evidence_ids=("E2",),
    )

    assert result.action == "REACTIVATED"
    assert graph.get("C1").status is NodeStatus.STALE
    assert graph.get("C2").status is NodeStatus.ACTIVE
    assert graph.downstream("E2") == ("C2",)
    assert graph.downstream("C2") == ("C1",)


def test_rebuild_rejects_invalidated_evidence() -> None:
    graph = ProvenanceGraph()
    graph.add_node(ProvenanceNode("E1", "evidence", "old source"))
    graph.add_node(ProvenanceNode("C1", "claim", "claim"))
    graph.add_edge(ProvenanceEdge("E1", "C1", "supports"))
    graph.invalidate("E1")

    try:
        ReEvaluationExecutor().rebuild(
            graph,
            stale_node="C1",
            replacement_node="C2",
            replacement_kind="claim",
            replacement_content="new claim",
            fresh_evidence_ids=("E1",),
        )
    except ValueError as exc:
        assert "active evidence" in str(exc)
    else:
        raise AssertionError("invalidated evidence must not reactivate a stale claim")
