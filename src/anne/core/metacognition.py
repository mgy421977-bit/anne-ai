"""Bounded metacognitive evaluation for ANNE.

Metacognition here means inspecting the state of a reasoning process before
allowing it to proceed. It is a deterministic engineering gate, not a claim
of consciousness or human-like self-awareness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from anne.core.decision_synthesis import DecisionStatus, DecisionSynthesis


class MetaStatus(StrEnum):
    READY = "READY"
    REVIEW = "REVIEW"
    ABSTAIN = "ABSTAIN"


class MetaFinding(StrEnum):
    EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    MULTIPLE_SUPPORTED = "MULTIPLE_SUPPORTED"
    CONTRADICTION_PRESENT = "CONTRADICTION_PRESENT"
    FAILURE_RECURRING = "FAILURE_RECURRING"
    FAILURE_TRACE_PRESENT = "FAILURE_TRACE_PRESENT"
    NO_SELECTED_HYPOTHESIS = "NO_SELECTED_HYPOTHESIS"
    SELECTED_HYPOTHESIS = "SELECTED_HYPOTHESIS"


@dataclass(frozen=True)
class MetaObservation:
    finding: MetaFinding
    detail: str


@dataclass
class MetacognitiveReview:
    status: MetaStatus
    observations: list[MetaObservation] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    next_action: list[str] = field(default_factory=list)
    confidence_note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "observations": [asdict(item) for item in self.observations],
            "uncertainty": list(self.uncertainty),
            "checks": dict(self.checks),
            "next_action": list(self.next_action),
            "confidence_note": self.confidence_note,
        }


class MetacognitiveEvaluator:
    """Inspect a completed synthesis without changing its evidence."""

    def evaluate(
        self,
        synthesis: DecisionSynthesis,
        *,
        declared_confidence: float | None = None,
    ) -> MetacognitiveReview:
        observations: list[MetaObservation] = []
        uncertainty: list[str] = []
        checks = {
            "evidence_available": bool(synthesis.evidence),
            "selected_hypothesis_exists": synthesis.selected_hypothesis is not None,
            "contradictions_resolved": not bool(synthesis.contradictions),
            "failure_trace_clear": not bool(synthesis.failure_trace),
            "confidence_declared": declared_confidence is not None,
        }

        if synthesis.evidence:
            observations.append(MetaObservation(
                MetaFinding.EVIDENCE_SUFFICIENT,
                "At least one explicit evidence relation is present.",
            ))
        else:
            observations.append(MetaObservation(
                MetaFinding.EVIDENCE_INSUFFICIENT,
                "No evidence relation is attached to the synthesis.",
            ))
            uncertainty.append("No explicit evidence relation is available.")

        if synthesis.status is DecisionStatus.MULTIPLE_SUPPORTED:
            observations.append(MetaObservation(
                MetaFinding.MULTIPLE_SUPPORTED,
                "Multiple hypotheses remain supported; selection is not justified by synthesis alone.",
            ))
            uncertainty.append("More than one hypothesis remains supported.")
        elif synthesis.selected_hypothesis:
            observations.append(MetaObservation(
                MetaFinding.SELECTED_HYPOTHESIS,
                f"Hypothesis {synthesis.selected_hypothesis} is selected by the synthesis.",
            ))
        else:
            observations.append(MetaObservation(
                MetaFinding.NO_SELECTED_HYPOTHESIS,
                "No hypothesis is selected.",
            ))

        if synthesis.contradictions:
            observations.append(MetaObservation(
                MetaFinding.CONTRADICTION_PRESENT,
                f"{len(synthesis.contradictions)} hypothesis path(s) retain contradiction signals.",
            ))
            uncertainty.append("Contradictory evidence remains in the reasoning state.")

        if synthesis.failure_trace:
            observations.append(MetaObservation(
                MetaFinding.FAILURE_TRACE_PRESENT,
                f"{len(synthesis.failure_trace)} failure trace record(s) require review.",
            ))

        repeated_failure = self._has_repeated_failure(synthesis.failure_trace)
        if repeated_failure:
            observations.append(MetaObservation(
                MetaFinding.FAILURE_RECURRING,
                "A failure identifier or reason recurs; the same reasoning path should not be retried unchanged.",
            ))
            uncertainty.append("A repeated failure signal was detected.")

        confidence_note = self._confidence_note(declared_confidence)
        if declared_confidence is not None and not 0.0 <= declared_confidence <= 1.0:
            raise ValueError("declared_confidence must be between 0 and 1")

        status = self._status(synthesis, repeated_failure)
        next_action = self._next_action(status, synthesis, repeated_failure)

        return MetacognitiveReview(
            status=status,
            observations=observations,
            uncertainty=uncertainty,
            checks=checks,
            next_action=next_action,
            confidence_note=confidence_note,
        )

    @staticmethod
    def _has_repeated_failure(trace: list[dict[str, Any]]) -> bool:
        seen: set[str] = set()
        for item in trace:
            key = str(item.get("id") or item.get("reason") or "").strip().casefold()
            if not key:
                continue
            if key in seen:
                return True
            seen.add(key)
        return False

    @staticmethod
    def _confidence_note(confidence: float | None) -> str:
        if confidence is None:
            return "No confidence value supplied; do not infer confidence from wording."
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("declared_confidence must be between 0 and 1")
        if confidence >= 0.9:
            return "High declared confidence still requires evidence and contradiction checks."
        if confidence <= 0.5:
            return "Low declared confidence should remain visible and may justify further verification."
        return "Declared confidence is moderate; evidence state remains authoritative."

    @staticmethod
    def _status(
        synthesis: DecisionSynthesis,
        repeated_failure: bool,
    ) -> MetaStatus:
        if synthesis.status in {
            DecisionStatus.INSUFFICIENT_EVIDENCE,
            DecisionStatus.REJECTED,
            DecisionStatus.REJECTED_WITH_ALTERNATIVES,
        }:
            return MetaStatus.ABSTAIN
        if (
            repeated_failure
            or synthesis.status in {
                DecisionStatus.MULTIPLE_SUPPORTED,
                DecisionStatus.CONFLICTING,
            }
            or synthesis.contradictions
            or synthesis.failure_trace
        ):
            return MetaStatus.REVIEW
        return MetaStatus.READY

    @staticmethod
    def _next_action(
        status: MetaStatus,
        synthesis: DecisionSynthesis,
        repeated_failure: bool,
    ) -> list[str]:
        if status is MetaStatus.READY:
            return ["Proceed to the next guarded stage."]
        actions: list[str] = []
        if synthesis.status is DecisionStatus.MULTIPLE_SUPPORTED:
            actions.append("Run a discriminating test before selecting a hypothesis.")
        if synthesis.contradictions:
            actions.append("Resolve or independently verify contradictory evidence.")
        if synthesis.failure_trace:
            actions.append("Inspect failure trace before retrying.")
        if repeated_failure:
            actions.append("Change the reasoning strategy; do not repeat the failed path unchanged.")
        if synthesis.status in {
            DecisionStatus.INSUFFICIENT_EVIDENCE,
            DecisionStatus.REJECTED,
            DecisionStatus.REJECTED_WITH_ALTERNATIVES,
        }:
            actions.append("Abstain until new evidence or a valid alternative path is available.")
        return actions or ["Request metacognitive review."]


__all__ = [
    "MetaFinding",
    "MetaObservation",
    "MetaStatus",
    "MetacognitiveEvaluator",
    "MetacognitiveReview",
]
