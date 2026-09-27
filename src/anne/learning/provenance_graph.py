from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Iterable


class NodeStatus(StrEnum):
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    STALE = "stale"


@dataclass(frozen=True)
class ProvenanceNode:
    node_id: str
    kind: str
    content: str
    status: NodeStatus = NodeStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not self.content.strip():
            raise ValueError("content must not be empty")


@dataclass(frozen=True)
class ProvenanceEdge:
    source_id: str
    target_id: str
    relation: str = "supports"

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ValueError("edge endpoints must not be empty")
        if not self.relation.strip():
            raise ValueError("relation must not be empty")


class ProvenanceGraph:
    """Small deterministic dependency graph for evidence-derived knowledge."""

    def __init__(self, nodes: Iterable[ProvenanceNode] = ()) -> None:
        self._nodes: dict[str, ProvenanceNode] = {}
        self._edges: list[ProvenanceEdge] = []
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: ProvenanceNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate node id: {node.node_id}")
        self._nodes[node.node_id] = node

    def add_edge(self, edge: ProvenanceEdge) -> None:
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            raise ValueError("edge endpoints must exist")
        if edge in self._edges:
            return
        self._edges.append(edge)

    def add_dependency(
        self,
        *,
        source_id: str,
        target_id: str,
        relation: str = "depends_on",
    ) -> None:
        """Register an explicit dependency without inferring its meaning."""
        self.add_edge(ProvenanceEdge(source_id, target_id, relation))

    def register_evidence_claim(
        self,
        *,
        evidence_id: str,
        evidence_content: str,
        claim_id: str,
        claim_content: str,
        relation: str = "supports",
    ) -> None:
        """Register an explicit Evidence -> Claim provenance relationship."""
        self.add_node(ProvenanceNode(evidence_id, "evidence", evidence_content))
        self.add_node(ProvenanceNode(claim_id, "claim", claim_content))
        self.add_edge(ProvenanceEdge(evidence_id, claim_id, relation))

    def invalidate(self, node_id: str) -> tuple[str, ...]:
        if node_id not in self._nodes:
            raise KeyError(node_id)

        affected: list[str] = []
        queue = [node_id]
        seen: set[str] = set()

        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)

            node = self._nodes[current]
            if node.status is NodeStatus.ACTIVE:
                self._nodes[current] = ProvenanceNode(
                    node.node_id, node.kind, node.content, NodeStatus.INVALIDATED
                )
            if current not in affected:
                affected.append(current)

            for edge in self._edges:
                if edge.source_id == current and edge.target_id not in seen:
                    target = self._nodes[edge.target_id]
                    if target.status is NodeStatus.ACTIVE:
                        self._nodes[edge.target_id] = ProvenanceNode(
                            target.node_id, target.kind, target.content, NodeStatus.STALE
                        )
                    queue.append(edge.target_id)

        return tuple(affected)

    def get(self, node_id: str) -> ProvenanceNode:
        return self._nodes[node_id]

    def downstream(self, node_id: str) -> tuple[str, ...]:
        if node_id not in self._nodes:
            raise KeyError(node_id)
        result: list[str] = []
        queue = [node_id]
        seen = {node_id}
        while queue:
            current = queue.pop(0)
            for edge in self._edges:
                if edge.source_id == current and edge.target_id not in seen:
                    seen.add(edge.target_id)
                    result.append(edge.target_id)
                    queue.append(edge.target_id)
        return tuple(result)

    def as_dict(self) -> dict[str, object]:
        return {
            "nodes": [
                {
                    "id": node.node_id,
                    "kind": node.kind,
                    "content": node.content,
                    "status": node.status.value,
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {"source": edge.source_id, "target": edge.target_id, "relation": edge.relation}
                for edge in self._edges
            ],
        }


__all__ = ["NodeStatus", "ProvenanceNode", "ProvenanceEdge", "ProvenanceGraph"]
