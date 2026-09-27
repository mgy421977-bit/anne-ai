from __future__ import annotations

from dataclasses import dataclass

from anne.learning.provenance_graph import NodeStatus, ProvenanceGraph


@dataclass(frozen=True)
class ReEvaluationPlan:
    invalidated_node: str
    stale_nodes: tuple[str, ...]
    action: str
    reason: str

    @property
    def requires_research(self) -> bool:
        return self.action == "RESEARCH"


class ReEvaluationPlanner:
    """Turn provenance invalidation into a bounded re-evaluation decision."""

    def create_plan(
        self,
        graph: ProvenanceGraph,
        invalidated_node: str,
    ) -> ReEvaluationPlan:
        affected = graph.invalidate(invalidated_node)
        stale = tuple(
            node_id
            for node_id in affected
            if node_id != invalidated_node
            and graph.get(node_id).status is NodeStatus.STALE
        )
        if stale:
            return ReEvaluationPlan(
                invalidated_node=invalidated_node,
                stale_nodes=stale,
                action="RESEARCH",
                reason=(
                    "A provenance dependency became invalid; stale downstream "
                    "results require re-evaluation."
                ),
            )
        return ReEvaluationPlan(
            invalidated_node=invalidated_node,
            stale_nodes=(),
            action="STOP",
            reason="The invalidated dependency has no stale downstream result.",
        )


__all__ = ["ReEvaluationPlan", "ReEvaluationPlanner"]
