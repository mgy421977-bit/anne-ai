"""Bounded failure -> reframe -> retry coordination for ANNE."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureKind(StrEnum):
    """Coarse failure classes used to choose a bounded recovery strategy."""

    FAIL_FAST = "fail_fast"
    SEMANTIC = "semantic"
    LOGIC = "logic"
    EVIDENCE_GAP = "evidence_gap"
    RESOURCE_INSUFFICIENCY = "resource_insufficiency"
    HYPOTHESIS_FAILURE = "hypothesis_failure"
    RELATION_GAP = "relation_gap"
    VERIFICATION_GAP = "verification_gap"
    AUTHORITY_GAP = "authority_gap"
    BUDGET = "budget"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureSignal:
    """A structured, non-authoritative description of one failed attempt."""

    kind: FailureKind
    reason: str
    stage: str
    cycle_id: str
    depth: int


@dataclass(frozen=True)
class ReframePlan:
    strategy: str
    question: str
    parent_cycle_id: str
    depth: int
    attempt: int


@dataclass(frozen=True)
class RetryDecision:
    allowed: bool
    reason: str
    next_attempt: int


class FailureRecoveryController:
    """Plan recovery without granting the recovery path extra authority."""

    _STRATEGIES = {
        FailureKind.FAIL_FAST: "narrow_scope",
        FailureKind.SEMANTIC: "clarify_claim",
        FailureKind.LOGIC: "restate_assumptions",
        FailureKind.EVIDENCE_GAP: "seek_missing_evidence",
        FailureKind.RESOURCE_INSUFFICIENCY: "escalate_computation",
        FailureKind.HYPOTHESIS_FAILURE: "generate_new_hypothesis",
        FailureKind.RELATION_GAP: "expand_relation_analysis",
        FailureKind.VERIFICATION_GAP: "seek_verification",
        FailureKind.AUTHORITY_GAP: "request_authority_review",
        FailureKind.BUDGET: "reduce_scope",
        FailureKind.UNKNOWN: "restate_problem",
    }

    @classmethod
    def classify(cls, reason: str, stage: str) -> FailureKind:
        text = f"{stage} {reason}".casefold()
        if "fail_fast" in text or stage.upper() == "FAIL_FAST":
            return FailureKind.FAIL_FAST
        if any(x in text for x in ("authority", "permission", "authorization")):
            return FailureKind.AUTHORITY_GAP
        if any(x in text for x in ("verification", "cannot verify", "unverified")):
            return FailureKind.VERIFICATION_GAP
        if any(x in text for x in ("resource", "compute", "computation", "timeout", "capacity")):
            return FailureKind.RESOURCE_INSUFFICIENCY
        if any(x in text for x in ("wrong hypothesis", "hypothesis failure", "hypothesis rejected")):
            return FailureKind.HYPOTHESIS_FAILURE
        if any(x in text for x in ("relation gap", "relation analysis", "contradiction graph")):
            return FailureKind.RELATION_GAP
        if "semantic" in text:
            return FailureKind.SEMANTIC
        if "logic" in text or "invalid" in text:
            return FailureKind.LOGIC
        if any(x in text for x in ("gap", "missing", "insufficient evidence", "unknown", "uncertain")):
            return FailureKind.EVIDENCE_GAP
        if "budget" in text or "iteration" in text or "depth" in text:
            return FailureKind.BUDGET
        return FailureKind.UNKNOWN

    _EXPLICIT_STRATEGY_PREFIXES = {
        "seek_missing_evidence": "Identify the missing evidence: ",
        "seek_fresh_independent_evidence": "Seek fresh independent evidence for: ",
        "recheck_independent_evidence": "Recheck the claim against independent evidence: ",
        "clarify_claim": "Clarify the claim: ",
        "clarify_and_reframe": "Clarify and reframe the problem: ",
        "restate_assumptions": "Restate the assumptions: ",
        "rebuild_reasoning_from_constraints": "Rebuild the reasoning from constraints: ",
        "reduce_scope": "Reduce the problem scope: ",
        "narrow_claim_and_expose_uncertainty": "Narrow the claim and expose uncertainty: ",
        "reorder_and_verify_steps": "Reorder and verify the steps: ",
        "narrow_scope": "Narrow the problem scope: ",
        "restate_problem": "Restate the problem: ",
        "escalate_computation": "Escalate computation for: ",
        "generate_new_hypothesis": "Generate a new hypothesis for: ",
        "expand_relation_analysis": "Expand relation analysis for: ",
        "seek_verification": "Seek independent verification for: ",
        "request_authority_review": "Request authority review for: ",
    }

    @classmethod
    def plan(cls, failure: FailureSignal, question: str, *, attempt: int,
             preferred_strategy: str | None = None) -> ReframePlan:
        strategy = preferred_strategy or cls._STRATEGIES.get(failure.kind, "restate_problem")
        if strategy not in cls._EXPLICIT_STRATEGY_PREFIXES:
            strategy = cls._STRATEGIES.get(failure.kind, "restate_problem")
        return ReframePlan(
            strategy=strategy,
            question=cls._EXPLICIT_STRATEGY_PREFIXES[strategy] + question.strip(),
            parent_cycle_id=failure.cycle_id,
            depth=failure.depth + 1,
            attempt=attempt,
        )

    @staticmethod
    def authorize_retry(*, attempt: int, max_retries: int,
                        seen_questions: set[str], question: str) -> RetryDecision:
        next_attempt = attempt + 1
        if next_attempt > max_retries:
            return RetryDecision(False, "retry_budget_exhausted", next_attempt)
        normalized = " ".join(question.casefold().split())
        if normalized in seen_questions:
            return RetryDecision(False, "oscillation_detected", next_attempt)
        return RetryDecision(True, "retry_authorized", next_attempt)


__all__ = [
    "FailureKind", "FailureRecoveryController", "FailureSignal",
    "ReframePlan", "RetryDecision",
]
