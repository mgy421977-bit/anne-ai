"""Deterministic decision synthesis for ANNE.

This module keeps alternative hypotheses visible while turning bounded evidence
and contradiction signals into an explicit, testable decision state. It does
not manufacture evidence and does not silently select a single hypothesis when
multiple hypotheses remain supported.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class HypothesisStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DecisionStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    MULTIPLE_SUPPORTED = "MULTIPLE_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECTED_WITH_ALTERNATIVES = "REJECTED_WITH_ALTERNATIVES"
    REJECTED = "REJECTED"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class EvidenceLink:
    """A bounded evidence relation already classified upstream."""

    evidence_id: str
    hypothesis_id: str
    relation: EvidenceRelation
    weight: float = 1.0
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if not self.hypothesis_id.strip():
            raise ValueError("hypothesis_id is required")
        if self.weight < 0:
            raise ValueError("weight must be non-negative")


@dataclass
class SynthesisHypothesis:
    """A hypothesis plus its evidence-derived state."""

    id: str
    claim: str
    evidence: list[EvidenceLink] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.UNCERTAIN
    support_score: float = 0.0
    contradiction_score: float = 0.0
    reason: list[str] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        return self.support_score - self.contradiction_score

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["evidence"] = [
            {**asdict(item), "relation": item.relation.value}
            for item in self.evidence
        ]
        data["net_score"] = self.net_score
        return data


@dataclass
class DecisionSynthesis:
    """Complete, serializable decision-synthesis contract."""

    status: DecisionStatus
    hypotheses: list[SynthesisHypothesis]
    selected_hypothesis: str | None = None
    evidence: list[EvidenceLink] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    failure_trace: list[dict[str, Any]] = field(default_factory=list)
    reason: list[str] = field(default_factory=list)
    next_action: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": {
                "status": self.status.value,
                "selected_hypothesis": self.selected_hypothesis,
            },
            "hypotheses": [item.as_dict() for item in self.hypotheses],
            "evidence": [
                {**asdict(item), "relation": item.relation.value}
                for item in self.evidence
            ],
            "contradictions": list(self.contradictions),
            "uncertainties": list(self.uncertainties),
            "failure_trace": list(self.failure_trace),
            "reason": list(self.reason),
            "next_action": list(self.next_action),
        }


class DecisionSynthesizer:
    """Deterministic synthesis layer; it never invents evidence."""

    def synthesize(
        self,
        hypotheses: list[SynthesisHypothesis],
        *,
        evidence: list[EvidenceLink] | None = None,
        failure_trace: list[dict[str, Any]] | None = None,
    ) -> DecisionSynthesis:
        items = [
            SynthesisHypothesis(
                id=h.id,
                claim=h.claim,
                evidence=list(h.evidence),
                status=h.status,
                support_score=h.support_score,
                contradiction_score=h.contradiction_score,
                reason=list(h.reason),
            )
            for h in hypotheses
        ]
        links = list(evidence or [])
        failures = list(failure_trace or [])

        if not items:
            return DecisionSynthesis(
                status=DecisionStatus.INSUFFICIENT_EVIDENCE,
                hypotheses=[],
                evidence=links,
                uncertainties=["No hypotheses were supplied."],
                failure_trace=failures,
                reason=["Decision synthesis cannot select or reject a hypothesis without alternatives."],
                next_action=["Generate at least one testable hypothesis."],
            )

        by_id = {item.id: item for item in items}
        for link in links:
            target = by_id.get(link.hypothesis_id)
            if target is None:
                continue
            target.evidence.append(link)
            if link.relation is EvidenceRelation.SUPPORTS:
                target.support_score += link.weight
            elif link.relation is EvidenceRelation.CONTRADICTS:
                target.contradiction_score += link.weight

        contradictions: list[str] = []
        uncertainties: list[str] = []
        for item in items:
            if item.support_score == 0 and item.contradiction_score == 0:
                item.status = HypothesisStatus.INSUFFICIENT_EVIDENCE
                uncertainties.append(item.id)
                continue
            if item.contradiction_score > item.support_score:
                item.status = HypothesisStatus.REJECTED
                item.reason.append("Contradictory evidence outweighs supporting evidence.")
                contradictions.append(item.id)
                continue
            if item.support_score == item.contradiction_score:
                item.status = HypothesisStatus.CONTRADICTED
                item.reason.append("Supporting and contradictory evidence are balanced.")
                contradictions.append(item.id)
                continue
            if item.contradiction_score > 0:
                item.status = HypothesisStatus.PARTIALLY_SUPPORTED
                item.reason.append("Supporting evidence exists, but contradictory evidence remains.")
                contradictions.append(item.id)
            else:
                item.status = HypothesisStatus.SUPPORTED

        supported = [
            item for item in items if item.status is HypothesisStatus.SUPPORTED
        ]
        partial = [
            item for item in items if item.status is HypothesisStatus.PARTIALLY_SUPPORTED
        ]

        if supported:
            if len(supported) == 1:
                status = DecisionStatus.SUPPORTED
                selected = supported[0].id
                reason = [f"{selected} is supported without contradictory evidence."]
            else:
                status = DecisionStatus.MULTIPLE_SUPPORTED
                selected = None
                reason = [
                    "Multiple hypotheses remain supported; no hypothesis is silently discarded."
                ]
            if partial:
                reason.append("Partially supported alternatives remain visible.")
        elif partial:
            status = DecisionStatus.CONFLICTING
            selected = None
            reason = ["Evidence supports alternatives but contradictions remain unresolved."]
        elif all(item.status is HypothesisStatus.REJECTED for item in items):
            status = DecisionStatus.REJECTED
            selected = None
            reason = ["All supplied hypotheses are rejected by the available evidence."]
        elif contradictions:
            status = DecisionStatus.REJECTED_WITH_ALTERNATIVES
            selected = None
            reason = ["Current hypotheses are contradicted or unresolved; alternatives require further testing."]
        else:
            status = DecisionStatus.INSUFFICIENT_EVIDENCE
            selected = None
            reason = ["Available evidence is insufficient to support a bounded decision."]

        next_action: list[str] = []
        if status in {
            DecisionStatus.CONFLICTING,
            DecisionStatus.INSUFFICIENT_EVIDENCE,
            DecisionStatus.REJECTED_WITH_ALTERNATIVES,
        }:
            next_action.append("Collect or generate discriminating evidence.")
        if contradictions:
            next_action.append("Trace the source and cause of contradictory evidence.")
        if failures:
            next_action.append("Review failure traces before retrying the same reasoning path.")
        if status is DecisionStatus.MULTIPLE_SUPPORTED:
            next_action.append("Run a discriminating test before selecting between supported hypotheses.")

        return DecisionSynthesis(
            status=status,
            hypotheses=items,
            selected_hypothesis=selected,
            evidence=links,
            contradictions=contradictions,
            uncertainties=uncertainties,
            failure_trace=failures,
            reason=reason,
            next_action=next_action,
        )


__all__ = [
    "DecisionStatus",
    "DecisionSynthesis",
    "DecisionSynthesizer",
    "EvidenceLink",
    "EvidenceRelation",
    "HypothesisStatus",
    "SynthesisHypothesis",
]
