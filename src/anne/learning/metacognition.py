"""Bounded metacognitive assessment for canonical ANNE traces."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.trace import CycleTrace


@dataclass(frozen=True)
class MetacognitiveAssessment:
    """Explicit account of knowledge, uncertainty and decision dependencies."""

    known: tuple[str, ...]
    unknown: tuple[str, ...]
    evidence_basis: tuple[str, ...]
    assumptions: tuple[str, ...]
    decision_dependencies: tuple[str, ...]
    recalibration_triggers: tuple[str, ...]


class Metacognition:
    """Assess a trace without converting confidence into truth."""

    def assess(self, trace: CycleTrace) -> MetacognitiveAssessment:
        known: list[str] = []
        unknown: list[str] = []
        evidence_basis: list[str] = []
        assumptions: list[str] = []
        dependencies: list[str] = []
        triggers: list[str] = []

        verification = trace.verification
        decision = trace.decision
        status = str(
            verification.get(
                "verification_status",
                verification.get("status", "UNVERIFIED"),
            )
        ).upper()

        if status == "VERIFIED":
            known.append("verification status is explicitly VERIFIED")
        else:
            unknown.append("factual status is not established as VERIFIED")
            triggers.append("new_independent_evidence")

        sources = verification.get("verification_sources", ())
        if sources:
            evidence_basis.append("verification_sources")
        else:
            unknown.append("verification source provenance is not recorded")
            triggers.append("provenance_completion")

        reason = str(decision.get("reason", "")).strip()
        if reason:
            dependencies.append("decision_reason")

        if trace.intent:
            dependencies.append("intent")
        else:
            assumptions.append("intent is not explicitly recorded")
            triggers.append("intent_clarification")

        if trace.hypotheses:
            dependencies.append("hypotheses")
        else:
            assumptions.append("hypothesis state is not recorded")

        if trace.learning:
            dependencies.append("prior_learning_observation")

        if trace.stop_reason:
            dependencies.append("stop_reason")

        return MetacognitiveAssessment(
            tuple(known),
            tuple(dict.fromkeys(unknown)),
            tuple(dict.fromkeys(evidence_basis)),
            tuple(dict.fromkeys(assumptions)),
            tuple(dict.fromkeys(dependencies)),
            tuple(dict.fromkeys(triggers)),
        )


__all__ = ["Metacognition", "MetacognitiveAssessment"]
