"""Bounded metacognitive review of ANNE decision state.

This layer audits how a result was reached. It does not create authority,
upgrade evidence, or replace EvidenceGate, AgencyGate, or Decision Synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.cognitive_state import CognitiveState


@dataclass(frozen=True)
class MetacognitiveAssessment:
    """Inspectable post-decision assessment without epistemic or authority power."""

    evidence_status: str
    evidence_sufficient: bool
    has_conflict: bool
    alternatives_preserved: tuple[str, ...]
    needs_research: bool
    uncertainty: float
    ambiguity: float
    agency_decision: str | None
    core_decision: str | None
    reason: str


class MetacognitiveReviewer:
    """Review explicit state and report unresolved cognitive conditions."""

    _RESEARCH_STATUSES = {
        "missing",
        "unverified",
        "conflicting",
        "refuted",
    }

    def review(self, state: CognitiveState) -> MetacognitiveAssessment:
        status_value = state.context_map.get("evidence_status", state.evidence_status)
        status = str(status_value)
        verified_value = state.context_map.get(
            "evidence_verified", state.evidence_verified
        )
        evidence_sufficient = (
            not state.requires_evidence
            or status == "verified" and bool(verified_value)
        )

        verification_status = str(
            state.context_map.get("verification_status", "")
        ).lower()
        synthesis_status = str(
            state.context_map.get("decision_synthesis_status", "")
        ).lower()
        has_conflict = (
            status == "conflicting"
            or verification_status == "conflicting"
            or synthesis_status == "conflicting"
        )

        alternatives = self._alternatives(state)
        needs_research = state.requires_evidence and (
            not evidence_sufficient or has_conflict
        )

        uncertainty = self._uncertainty(
            state,
            evidence_sufficient=evidence_sufficient,
            has_conflict=has_conflict,
        )
        reason = self._reason(
            status=status,
            evidence_sufficient=evidence_sufficient,
            has_conflict=has_conflict,
            needs_research=needs_research,
            alternatives=alternatives,
        )

        return MetacognitiveAssessment(
            evidence_status=status,
            evidence_sufficient=evidence_sufficient,
            has_conflict=has_conflict,
            alternatives_preserved=alternatives,
            needs_research=needs_research,
            uncertainty=uncertainty,
            ambiguity=state.ambiguity,
            agency_decision=self._optional_string(state.context_map.get("agency_gate")),
            core_decision=self._optional_string(state.context_map.get("core_decision")),
            reason=reason,
        )

    @staticmethod
    def _alternatives(state: CognitiveState) -> tuple[str, ...]:
        values: list[str] = []

        for item in state.low_prob_preserved:
            hypothesis = item.get("hypothesis")
            if isinstance(hypothesis, str) and hypothesis.strip():
                values.append(hypothesis.strip())

        raw = state.context_map.get("decision_synthesis_alternatives", ())
        if isinstance(raw, (list, tuple)):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())

        # Preserve order while removing duplicates.
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _uncertainty(
        state: CognitiveState,
        *,
        evidence_sufficient: bool,
        has_conflict: bool,
    ) -> float:
        uncertainty = min(max(state.ambiguity, 0.0), 1.0)
        if not evidence_sufficient:
            uncertainty = max(uncertainty, 0.7)
        if has_conflict:
            uncertainty = max(uncertainty, 0.9)
        return round(uncertainty, 3)

    @staticmethod
    def _reason(
        *,
        status: str,
        evidence_sufficient: bool,
        has_conflict: bool,
        needs_research: bool,
        alternatives: tuple[str, ...],
    ) -> str:
        if has_conflict:
            return (
                "Conflicting evidence or synthesis remains unresolved; "
                "alternatives are preserved and further research may be required."
            )
        if not evidence_sufficient:
            return (
                f"Evidence status is {status}; the result is not epistemically "
                "sufficient for a research-required conclusion."
            )
        if alternatives:
            return (
                "Evidence is sufficient for the current state; preserved alternatives "
                "remain visible for later reassessment."
            )
        if needs_research:
            return (
                "Further bounded research is required before the result can be "
                "treated as sufficient."
            )
        return (
            "Current evidence state is sufficient and no unresolved alternative "
            "was recorded."
        )


__all__ = ["MetacognitiveAssessment", "MetacognitiveReviewer"]
