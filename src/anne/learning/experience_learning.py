"""Bounded extraction of reusable experience from canonical traces.

Experience is an observation about a prior cycle, not a new source of truth.
It is deliberately marked non-reusable until a separate strategy gate permits
reuse under the current conditions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from anne.core.self_correction import FailureClass, SelfCorrectionPlanner
from anne.core.trace import CycleTrace
from anne.learning.context_fingerprint import ExplicitContextFingerprint


@dataclass(frozen=True)
class Experience:
    source_cycle_id: str
    outcome: str
    failure_class: str
    strategy: str
    lesson: str
    safe_to_reuse: bool
    factual_status: str
    context_key: str = ""
    context_conditions: tuple[tuple[str, str], ...] = ()
    parent_cycle_id: str | None = None
    lineage: tuple[str, ...] = ()
    language_corroboration_status: str = ""
    language_corroboration_providers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized = ExplicitContextFingerprint(
            self.context_key, self.context_conditions
        )
        object.__setattr__(self, "context_key", normalized.key)
        object.__setattr__(self, "context_conditions", normalized.conditions)

    @property
    def context_fingerprint(self) -> tuple[
        str, str, tuple[tuple[str, str], ...]
    ]:
        return (self.failure_class, self.context_key, self.context_conditions)


class ExperienceLearner:
    """Convert observed traces into bounded, non-authoritative experience."""

    def __init__(
        self,
        planner: SelfCorrectionPlanner | None = None,
        *,
        max_context_conditions: int = 16,
    ) -> None:
        if max_context_conditions < 1:
            raise ValueError("max_context_conditions must be positive")
        self.planner = planner or SelfCorrectionPlanner()
        self.max_context_conditions = max_context_conditions

    def from_trace(self, trace: CycleTrace, *, strategy: str = "") -> Experience:
        reason = trace.stop_reason or ""
        if trace.errors:
            reason = f"{reason} " + " ".join(
                str(error.get("reason", "")) for error in trace.errors
            )

        failure_class = self.planner.classify(trace.stop_reason, reason)
        outcome = (
            "SUCCESS"
            if trace.status.upper() in {"EXECUTED", "SUCCESS"} and not trace.errors
            else "FAILURE"
        )

        if outcome == "SUCCESS":
            failure_class = FailureClass.UNKNOWN

        raw_factual_status = trace.verification.get(
            "verification_status",
            trace.verification.get("status"),
        )
        intent_recorded = "intent" in trace.intent
        evidence_required = (
            intent_recorded
            and trace.intent.get("requires_evidence", True) is not False
        )
        factual_status = (
            str(raw_factual_status).upper()
            if raw_factual_status is not None
            else ("UNVERIFIED" if evidence_required or not intent_recorded else "NOT_REQUIRED")
        )
        lesson = (
            f"Observed {outcome.lower()} for strategy "
            f"'{strategy or 'unspecified'}'; "
            "do not promote this observation to truth."
        )
        context = trace.learning.get("context", {})
        explicit = ExplicitContextFingerprint.from_context(
            context if isinstance(context, Mapping) else {},
            max_conditions=self.max_context_conditions,
        )
        language = trace.language_corroboration
        language_status = (
            str(language.get("status", "")).lower()
            if isinstance(language, Mapping)
            else ""
        )
        language_providers = (
            tuple(str(provider) for provider in language.get("providers", ()))
            if isinstance(language, Mapping)
            else ()
        )
        return Experience(
            source_cycle_id=trace.cycle_id,
            outcome=outcome,
            failure_class=failure_class.value,
            strategy=strategy,
            lesson=lesson,
            safe_to_reuse=False,
            factual_status=factual_status,
            context_key=explicit.key,
            context_conditions=explicit.conditions,
            parent_cycle_id=trace.parent_cycle_id,
            lineage=trace.lineage,
            language_corroboration_status=language_status,
            language_corroboration_providers=language_providers,
        )


__all__ = ["Experience", "ExperienceLearner"]
