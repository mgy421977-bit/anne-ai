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

        sources = verification.get("verification_sources", ())
        has_sources = bool(sources)
        if status == "VERIFIED" and has_sources:
            known.append("verification status is explicitly VERIFIED with recorded sources")
        else:
            unknown.append("factual status is not established as VERIFIED with recorded provenance")
            if status == "CONFLICTING":
                triggers.append("resolve_conflicting_evidence")
            elif status == "REFUTED":
                triggers.append("reassess_refuted_claim")
            else:
                triggers.append("new_independent_evidence")

        if has_sources:
            evidence_basis.append("verification_sources")
        else:
            unknown.append("verification source provenance is not recorded")
            triggers.append("provenance_completion")

        reason = str(decision.get("reason", "")).strip()
        if reason:
            dependencies.append("decision_reason")
        decision_status = str(
            decision.get("status", decision.get("verdict", ""))
        ).upper()
        if decision_status in {"REVIEW", "ABSTAIN", "INSUFFICIENT_EVIDENCE", "CONFLICTING"}:
            dependencies.append("decision_status")
            triggers.append("decision_reassessment")

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
        else:
            assumptions.append("prior learning observation is not recorded")

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
