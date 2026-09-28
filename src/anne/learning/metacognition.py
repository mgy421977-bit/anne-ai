"""Bounded metacognitive assessment for the ANNE cognitive pipeline.

This layer observes an already-produced cognitive state and makes the reasoning
trace explicit. It does not create authority, verify evidence, or override
EvidenceGate/AgencyGate decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from anne.core.cognitive_state import CognitiveState, Hypothesis
from anne.learning.evidence import EvidenceItem, SupportStatus


@dataclass(frozen=True)
class MetacognitiveAssessment:
    """Inspectable self-evaluation of one bounded reasoning cycle."""

    action: str
    epistemic_status: str
    evidence_count: int
    supporting_evidence: int
    contradicting_evidence: int
    unclear_evidence: int
    alternatives: tuple[str, ...]
    contradiction_detected: bool
    uncertainty: float
    further_research_required: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.evidence_count,
            self.supporting_evidence,
            self.contradicting_evidence,
            self.unclear_evidence,
        ):
            if value < 0:
                raise ValueError("evidence counts must be non-negative")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be between 0.0 and 1.0")
        if self.supporting_evidence + self.contradicting_evidence + self.unclear_evidence != self.evidence_count:
            raise ValueError("evidence counts must sum to evidence_count")


class MetacognitiveEvaluator:
    """Build a bounded, deterministic reasoning self-assessment.

    The evaluator only observes supplied state, hypotheses and evidence.
    It never infers evidence support from text similarity and never changes
    the underlying cognitive decision.
    """

    def assess(
        self,
        state: CognitiveState,
        hypothesis: Hypothesis | None = None,
        hypotheses: Sequence[Hypothesis] = (),
        evidence: Sequence[EvidenceItem] = (),
    ) -> MetacognitiveAssessment:
        items = tuple(evidence)
        supporting = sum(item.support == SupportStatus.SUPPORTS.value for item in items)
        contradicting = sum(
            item.support == SupportStatus.CONTRADICTS.value for item in items
        )
        unclear = len(items) - supporting - contradicting

        alternatives = tuple(
            candidate.claim
            for candidate in hypotheses
            if not hypothesis or candidate.id != hypothesis.id
        )

        reasons: list[str] = []
        uncertainty = max(0.0, min(1.0, state.ambiguity))

        if state.requires_evidence:
            if state.evidence_status != "verified":
                reasons.append(
                    f"evidence status is {state.evidence_status}; verification is incomplete"
                )
                uncertainty = max(uncertainty, 0.7)

        if contradicting:
            reasons.append("contradictory evidence is present")
            uncertainty = max(uncertainty, 0.8)

        if unclear:
            reasons.append("some evidence has unclear support status")
            uncertainty = max(uncertainty, 0.6)

        if alternatives:
            reasons.append(f"{len(alternatives)} alternative hypothesis(es) remain explicit")

        if state.intent_confidence < 0.7:
            reasons.append("intent classification confidence is below 0.7")
            uncertainty = max(uncertainty, 1.0 - state.intent_confidence)

        if state.context_map.get("anla_passed") is False:
            reasons.append("ANLA semantic validation did not pass")
            uncertainty = max(uncertainty, 0.9)

        if not reasons:
            reasons.append("no additional metacognitive warning was detected")

        further_research = (
            state.requires_evidence
            and (
                state.evidence_status != "verified"
                or contradicting > 0
                or unclear > 0
            )
        )

        return MetacognitiveAssessment(
            action=state.action,
            epistemic_status=state.evidence_status,
            evidence_count=len(items),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            unclear_evidence=unclear,
            alternatives=alternatives,
            contradiction_detected=contradicting > 0 and supporting > 0,
            uncertainty=round(uncertainty, 3),
            further_research_required=further_research,
            reasons=tuple(reasons),
        )


__all__ = ["MetacognitiveAssessment", "MetacognitiveEvaluator"]
