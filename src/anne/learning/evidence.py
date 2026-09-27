"""Structured evidence records used by ANNE's learning/research layer."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from anne.learning.provenance_graph import (
    NodeStatus,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
)
from anne.learning.reevaluation import ReEvaluationPlan, ReEvaluationPlanner


class SupportStatus(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class EvidenceItem:
    """A provenance-carrying, non-authoritative piece of evidence."""

    source: str
    claim: str
    kind: str
    provenance: str
    confidence: float
    passage: str = ""
    support: str = SupportStatus.UNCLEAR.value

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not self.provenance.strip():
            raise ValueError("provenance must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class EvidenceDependency:
    """Link a derived claim to the evidence identifiers it depends on."""

    claim_id: str
    claim: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id must not be empty")
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.evidence_ids or any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must contain non-empty identifiers")


class EvidenceStatus(StrEnum):
    """Epistemic status for evidence retained by the cognitive workspace."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REFUTED = "refuted"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class EvidenceLedgerEntry:
    """Traceable evidence attached to a claim without upgrading it to truth."""

    claim: str
    source: str
    provenance: str
    confidence: float
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    passage: str = ""
    retrieved_at: str = ""
    support: str = SupportStatus.UNCLEAR.value

    def __post_init__(self) -> None:
        if not self.claim.strip():
            raise ValueError("claim must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.provenance.strip():
            raise ValueError("provenance must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        EvidenceStatus(self.status)
        if not self.retrieved_at:
            object.__setattr__(self, "retrieved_at", datetime.now(UTC).isoformat())


class EvidenceLedger:
    """Evidence records plus explicit provenance dependencies.

    The ledger records evidence automatically, but claim/hypothesis/answer
    relationships must be registered explicitly; provenance is never inferred
    from text similarity.
    """

    def __init__(self) -> None:
        self._entries: dict[str, EvidenceLedgerEntry] = {}
        self.graph = ProvenanceGraph()

    @staticmethod
    def evidence_id(entry: EvidenceLedgerEntry) -> str:
        payload = "|".join((entry.provenance, entry.claim, entry.passage))
        return "E-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def record(self, entry: EvidenceLedgerEntry) -> str:
        evidence_id = self.evidence_id(entry)
        self._entries[evidence_id] = entry
        try:
            self.graph.get(evidence_id)
        except KeyError:
            self.graph.add_node(
                ProvenanceNode(evidence_id, "evidence", entry.passage or entry.claim)
            )
        return evidence_id

    def get(self, evidence_id: str) -> EvidenceLedgerEntry:
        return self._entries[evidence_id]

    def register_claim(
        self,
        *,
        claim_id: str,
        claim: str,
        evidence_ids: tuple[str, ...],
    ) -> None:
        if not evidence_ids:
            raise ValueError("evidence_ids must not be empty")
        self.graph.add_node(ProvenanceNode(claim_id, "claim", claim))
        for evidence_id in evidence_ids:
            if evidence_id not in self._entries:
                raise ValueError(f"unknown evidence id: {evidence_id}")
            self.graph.add_edge(ProvenanceEdge(evidence_id, claim_id, "supports"))

    def register_derivation(
        self,
        *,
        source_id: str,
        source_kind: str,
        target_id: str,
        target_kind: str,
        target_content: str,
        relation: str = "derived_from",
    ) -> None:
        try:
            self.graph.get(source_id)
        except KeyError as exc:
            raise ValueError(f"unknown source id: {source_id}") from exc
        self.graph.add_node(ProvenanceNode(target_id, target_kind, target_content))
        self.graph.add_edge(ProvenanceEdge(source_id, target_id, relation))

    def invalidate_evidence(self, evidence_id: str) -> tuple[str, ...]:
        if evidence_id not in self._entries:
            raise KeyError(evidence_id)
        return self.graph.invalidate(evidence_id)

    def re_evaluation_plan(self, evidence_id: str) -> ReEvaluationPlan:
        """Return the bounded re-evaluation action after invalidating evidence."""
        if evidence_id not in self._entries:
            raise KeyError(evidence_id)
        return ReEvaluationPlanner().create_plan(self.graph, evidence_id)

    def status(self, node_id: str) -> NodeStatus:
        return self.graph.get(node_id).status

    def provenance(self) -> dict[str, object]:
        return self.graph.as_dict()


__all__ = [
    "EvidenceItem",
    "EvidenceLedgerEntry",
    "EvidenceDependency",
    "EvidenceLedger",
    "EvidenceStatus",
    "SupportStatus",
]
