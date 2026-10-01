"""Bounded observational evaluation of strategy changes.

This module measures whether a changed strategy was followed by a different
observed outcome. It does not infer causality, truth, or authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyDecision


class StrategyEffectiveness(StrEnum):
    IMPROVED = "improved"
    NOT_IMPROVED = "not_improved"
    NO_CHANGE = "no_change"
    INSUFFICIENT_OBSERVATION = "insufficient_observation"


@dataclass(frozen=True)
class StrategyOutcome:
    strategy: str
    effectiveness: StrategyEffectiveness
    compared_cycle_ids: tuple[str, ...] = ()
    reason: str = ""
    causal_claim: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "effectiveness": self.effectiveness.value,
            "compared_cycle_ids": list(self.compared_cycle_ids),
            "reason": self.reason,
            "causal_claim": self.causal_claim,
        }


class StrategyOutcomeEvaluator:
    """Measure strategy changes conservatively from observed experiences."""

    def evaluate(
        self,
        decision: StrategyDecision,
        experiences: tuple[Experience, ...],
    ) -> StrategyOutcome:
        if not experiences:
            return StrategyOutcome(
                decision.strategy,
                StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
                reason="no_experience_observed",
            )

        latest = experiences[-1]
        if latest.strategy != decision.strategy:
            return StrategyOutcome(
                decision.strategy,
                StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
                (latest.source_cycle_id,),
                "latest_experience_does_not_match_selected_strategy",
            )

        if len(experiences) < 2:
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
                (latest.source_cycle_id,),
                "strategy_needs_a_comparable_prior_observation",
            )

        previous = experiences[-2]
        previous_context = (previous.context_key, previous.context_conditions)
        latest_context = (latest.context_key, latest.context_conditions)
        if previous_context != latest_context:
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
                (previous.source_cycle_id, latest.source_cycle_id),
                "observations_have_different_explicit_context_fingerprints",
            )

        lineage = set(latest.lineage)
        if (
            previous.source_cycle_id not in lineage
            and latest.parent_cycle_id != previous.source_cycle_id
        ):
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
                (previous.source_cycle_id, latest.source_cycle_id),
                "observations_are_not_in_the_same_explicit_cycle_lineage",
            )

        if previous.strategy == latest.strategy:
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.NO_CHANGE,
                (previous.source_cycle_id, latest.source_cycle_id),
                "strategy_did_not_change_between_observations",
            )

        compared = (previous.source_cycle_id, latest.source_cycle_id)
        if previous.outcome == "FAILURE" and latest.outcome == "SUCCESS":
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.IMPROVED,
                compared,
                "changed_strategy_was_followed_by_success_after_prior_failure",
            )
        if previous.outcome == "FAILURE" and latest.outcome == "FAILURE":
            return StrategyOutcome(
                latest.strategy,
                StrategyEffectiveness.NOT_IMPROVED,
                compared,
                "changed_strategy_was_followed_by_another_failure",
            )
        return StrategyOutcome(
            latest.strategy,
            StrategyEffectiveness.INSUFFICIENT_OBSERVATION,
            compared,
            "prior_observation_does_not_establish_a_comparable_failure_to_success_transition",
        )


__all__ = ["StrategyEffectiveness", "StrategyOutcome", "StrategyOutcomeEvaluator"]
