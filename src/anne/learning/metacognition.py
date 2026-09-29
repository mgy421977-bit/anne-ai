"""Bounded metacognitive assessment for canonical ANNE traces.

Metacognition evaluates the recorded reasoning process and identifies explicit
uncertainty or missing prerequisites. It does not certify truth, causality,
authority, or execution permission.
"""

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
    evaluation_status: str = "PROCESS_COMPLETE"
    research_required: bool = False
    research_reason: str = ""

    @property
    def requires_review(self) -> bool:
        return self.evaluation_status == "PROCESS_REVIEW_REQUIRED"


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
        raw_status = verification.get("verification_status", verification.get("status"))
        intent_requires_evidence = trace.intent.get("requires_evidence")
        evidence_required = intent_requires_evidence is True
        status = str(raw_status).upper() if raw_status is not None else (
            "UNVERIFIED" if evidence_required else "NOT_REQUIRED"
        )

        sources = verification.get("verification_sources", ())
        if status == "VERIFIED" and sources:
            known.append("verification status is explicitly VERIFIED")
        elif status == "VERIFIED":
            unknown.append("verification status is VERIFIED but provenance is incomplete")
            triggers.append("provenance_completion")
        elif status == "NOT_REQUIRED":
            known.append("verification is not required by the recorded intent")
        else:
            unknown.append("factual status is not established as VERIFIED")
            triggers.append("new_independent_evidence")

        if sources:
            evidence_basis.append("verification_sources")
        elif status != "NOT_REQUIRED":
            unknown.append("verification source provenance is not recorded")
            if "provenance_completion" not in triggers:
                triggers.append("provenance_completion")

        reason = str(decision.get("reason", "")).strip()
        if reason:
            dependencies.append("decision_reason")
        else:
            assumptions.append("decision reason is not explicitly recorded")
            triggers.append("decision_reason_recording")

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

        review_reasons: list[str] = []
        if status in {"UNVERIFIED", "CONFLICTING", "REFUTED"}:
            review_reasons.append("factual_status_requires_reassessment")
        if status == "VERIFIED" and not sources:
            review_reasons.append("verification_provenance_is_missing")
        if not trace.intent:
            review_reasons.append("intent_is_missing")
        if not reason:
            review_reasons.append("decision_reason_is_missing")

        research_required = status in {"UNVERIFIED", "CONFLICTING"} and evidence_required
        if research_required:
            research_reason = "verification_status_does_not_close_the_evidence_loop"
        elif status == "VERIFIED" and not sources:
            research_reason = "provenance_is_incomplete"
        else:
            research_reason = ""

        evaluation_status = (
            "PROCESS_REVIEW_REQUIRED" if review_reasons else "PROCESS_COMPLETE"
        )
        return MetacognitiveAssessment(
            tuple(known),
            tuple(dict.fromkeys(unknown)),
            tuple(dict.fromkeys(evidence_basis)),
            tuple(dict.fromkeys(assumptions)),
            tuple(dict.fromkeys(dependencies)),
            tuple(dict.fromkeys(triggers)),
            evaluation_status,
            research_required,
            research_reason,
        )


__all__ = ["Metacognition", "MetacognitiveAssessment"]
