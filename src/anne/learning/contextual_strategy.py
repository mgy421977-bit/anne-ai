"""Contextual selection among previously observed strategy outcomes.

Selection is bounded and observational: a strategy is preferred only when the
same failure context has produced usable prior observations. No truth or
authority is inferred from historical success.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.learning.experience_learning import Experience


@dataclass(frozen=True)
class StrategyContext:
    failure_class: str
    context_key: str = ""


@dataclass(frozen=True)
class StrategyCandidate:
    strategy: str
    observations: int
    successes: int
    failures: int
    source_cycle_ids: tuple[str, ...] = ()

    @property
    def success_rate(self) -> float:
        if self.observations == 0:
            return 0.0
        return self.successes / self.observations


@dataclass(frozen=True)
class ContextualStrategyChoice:
    strategy: str
    reason: str
    candidates: tuple[StrategyCandidate, ...]
    selected_by_observation: bool = False


class ContextualStrategySelector:
    """Select from observed candidates without inventing a strategy."""

    def select(
        self,
        context: StrategyContext,
        experiences: tuple[Experience, ...],
        candidates: tuple[str, ...],
    ) -> ContextualStrategyChoice:
        allowed = tuple(dict.fromkeys(candidates))
        observations: list[StrategyCandidate] = []

        for strategy in allowed:
            relevant = tuple(
                item
                for item in experiences
                if item.strategy == strategy
                and item.failure_class == context.failure_class
            )
            if not relevant:
                continue
            observations.append(
                StrategyCandidate(
                    strategy=strategy,
                    observations=len(relevant),
                    successes=sum(item.outcome == "SUCCESS" for item in relevant),
                    failures=sum(item.outcome == "FAILURE" for item in relevant),
                    source_cycle_ids=tuple(item.source_cycle_id for item in relevant),
                )
            )

        if not observations:
            fallback = allowed[0] if allowed else "reassess_without_assuming_cause"
            return ContextualStrategyChoice(
                fallback,
                "no_observed_candidate_for_context",
                (),
                False,
            )

        observations.sort(
            key=lambda item: (item.success_rate, item.observations),
            reverse=True,
        )
        selected = observations[0]
        return ContextualStrategyChoice(
            selected.strategy,
            "selected_from_observed_same_context_outcomes",
            tuple(observations),
            True,
        )


__all__ = [
    "ContextualStrategyChoice",
    "ContextualStrategySelector",
    "StrategyCandidate",
    "StrategyContext",
]
