from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from anne.learning.provenance_graph import NodeStatus, ProvenanceGraph, ProvenanceNode, ProvenanceEdge


@dataclass(frozen=True)
class ReEvaluationResult:
    """Result of explicitly rebuilding a stale node from fresh provenance."""

    stale_node: str
    replacement_node: str
    action: str
    reason: str


class ReEvaluationExecutor:
    """Apply an explicit fresh-evidence replacement without rewriting history."""

    def rebuild(
        self,
        graph: ProvenanceGraph,
        *,
        stale_node: str,
        replacement_node: str,
        replacement_kind: str,
        replacement_content: str,
        fresh_evidence_ids: Iterable[str],
    ) -> ReEvaluationResult:
        stale = graph.get(stale_node)
        if stale.status is not NodeStatus.STALE:
            raise ValueError("stale_node must have STALE status")
        if replacement_node in {
            node["id"] for node in graph.as_dict()["nodes"]
        }:
            raise ValueError(f"replacement node already exists: {replacement_node}")

        evidence_ids = tuple(dict.fromkeys(fresh_evidence_ids))
        if not evidence_ids:
            raise ValueError("fresh_evidence_ids must not be empty")
        for evidence_id in evidence_ids:
            evidence = graph.get(evidence_id)
            if evidence.kind != "evidence":
                raise ValueError(f"fresh dependency is not evidence: {evidence_id}")
            if evidence.status is not NodeStatus.ACTIVE:
                raise ValueError(
                    f"fresh dependency is not active evidence: {evidence_id}"
                )

        graph.add_node(
            ProvenanceNode(
                replacement_node,
                replacement_kind,
                replacement_content,
                NodeStatus.ACTIVE,
            )
        )
        for evidence_id in evidence_ids:
            graph.add_edge(
                ProvenanceEdge(evidence_id, replacement_node, "supports")
            )
        graph.add_edge(
            ProvenanceEdge(replacement_node, stale_node, "replaces")
        )

        return ReEvaluationResult(
            stale_node=stale_node,
            replacement_node=replacement_node,
            action="REACTIVATED",
            reason="Fresh active evidence produced an explicit replacement; historical stale state was preserved.",
        )


__all__ = ["ReEvaluationResult", "ReEvaluationExecutor"]
