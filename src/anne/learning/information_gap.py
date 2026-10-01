"""Bounded detection of information gaps from canonical cognitive traces."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.trace import CycleTrace


@dataclass(frozen=True)
class InformationGap:
    present: bool
    categories: tuple[str, ...] = ()
    reason: str = ""


class InformationGapDetector:
    """Detect missing knowledge without inferring facts from confidence."""

    def detect(self, trace: CycleTrace) -> InformationGap:
        verification = trace.verification
        decision = trace.decision
        categories: list[str] = []

        verification_status = str(
            verification.get("status", verification.get("verification_status", ""))
        ).upper()
        intent_recorded = bool(trace.intent)\n        evidence_required = intent_recorded and trace.intent.get("requires_evidence", True) is not False
        decision_status = str(
            decision.get("status", decision.get("verdict", ""))
        ).upper()

        if evidence_required and verification_status in {"UNVERIFIED", "CONFLICTING", "REFUTED"}:
            categories.append("evidence")
        if decision_status in {"INSUFFICIENT_EVIDENCE", "CONFLICTING"}:
            categories.append("decision_evidence")
        if evidence_required and not verification and not trace.evidence:
            categories.append("missing_trace_evidence")
        if any(
            "evidence" in str(error).lower() or "unknown" in str(error).lower()
            for error in trace.errors
        ):
            categories.append("explicit_gap")

        unique = tuple(dict.fromkeys(categories))
        if not unique:
            return InformationGap(False, (), "no_detected_gap")
        return InformationGap(True, unique, "knowledge_required_before_progress")


__all__ = ["InformationGap", "InformationGapDetector"]
