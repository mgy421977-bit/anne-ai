"""Bounded strategy adaptation from repeated experience."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from anne.learning.experience_learning import Experience


@dataclass(frozen=True)
class StrategyDecision:
    action: str
    strategy: str
    reason: str
    source_cycle_ids: tuple[str, ...] = ()


class StrategyAdapter:
    """Suggest a next strategy without changing safety or authority policy."""

    _ALTERNATIVES = {
        "evidence_gap": "seek_fresh_independent_evidence",
        "factual": "recheck_independent_evidence",
        "semantic": "clarify_and_reframe",
        "logical": "rebuild_reasoning_from_constraints",
        "procedural": "reorder_and_verify_steps",
        "uncertainty": "narrow_claim_and_expose_uncertainty",
    }

    def adapt(
        self,
        current_strategy: str,
        experiences: Sequence[Experience],
    ) -> StrategyDecision:
        failures = tuple(
            item for item in experiences
            if item.outcome == "FAILURE" and item.strategy == current_strategy
        )
        if not failures:
            return StrategyDecision("KEEP", current_strategy, "no_repeated_failure")
        if any(item.failure_class in {"ethical", "execution_risk"} for item in failures):
            return StrategyDecision(
                "ABSTAIN",
                "require_authority_review",
                "safety_or_authority_boundary_must_not_be_bypassed",
                tuple(item.source_cycle_id for item in failures),
            )
        if len(failures) < 3:
            return StrategyDecision(
                "KEEP",
                current_strategy,
                "single_failure_is_insufficient_for_strategy_change",
                tuple(item.source_cycle_id for item in failures),
            )
        classes = {item.failure_class for item in failures}
        if len(classes) != 1:
            return StrategyDecision(
                "ABSTAIN",
                "reassess_without_assuming_cause",
                "repeated_failures_have_different_causes",
                tuple(item.source_cycle_id for item in failures),
            )
        failure_class = next(iter(classes))
        alternative = self._ALTERNATIVES.get(failure_class)
        if alternative is None:
            return StrategyDecision(
                "ABSTAIN",
                "reassess_without_assuming_cause",
                "no_bounded_alternative_for_failure_class",
                tuple(item.source_cycle_id for item in failures),
            )
        return StrategyDecision(
            "CHANGE",
            alternative,
            "repeated_same_failure_supports_a_bounded_strategy_change",
            tuple(item.source_cycle_id for item in failures),
        )


__all__ = ["StrategyDecision", "StrategyAdapter"]
