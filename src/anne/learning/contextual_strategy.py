"""Contextual selection among previously observed strategy outcomes.

Selection is bounded and observational: a strategy is preferred only when the
same explicit context has produced usable prior observations. No truth,
causality, or authority is inferred from historical success.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.learning.experience_learning import Experience


@dataclass(frozen=True)
class StrategyContext:
    """Explicit, bounded context used for exact strategy reuse matching."""

    failure_class: str
    context_key: str = ""
    conditions: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(
            sorted({(str(key), str(value)) for key, value in self.conditions})
        )
        object.__setattr__(self, "conditions", normalized)

    @property
    def fingerprint(self) -> tuple[str, str, tuple[tuple[str, str], ...]]:
        """Return a deterministic fingerprint; no semantic similarity is used."""

        return (self.failure_class, self.context_key, self.conditions)


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

    def __init__(self, *, max_experiences: int = 64, max_candidates: int = 8) -> None:
        if max_experiences < 1 or max_candidates < 1:
            raise ValueError("selection bounds must be positive")
        self.max_experiences = max_experiences
        self.max_candidates = max_candidates

    def select(
        self,
        context: StrategyContext,
        experiences: tuple[Experience, ...],
        candidates: tuple[str, ...],
    ) -> ContextualStrategyChoice:
        allowed = tuple(dict.fromkeys(candidates))[: self.max_candidates]
        bounded_experiences = experiences[-self.max_experiences :]
        observations: list[StrategyCandidate] = []

        for strategy in allowed:
            relevant = tuple(
                item
                for item in bounded_experiences
                if item.strategy == strategy
                and item.context_fingerprint == context.fingerprint
            )
            if not relevant:
                continue
            observations.append(
                StrategyCandidate(
                    strategy=strategy,
                    observations=len(relevant),
                    successes=sum(
                        item.outcome == "SUCCESS" for item in relevant
                    ),
                    failures=sum(item.outcome == "FAILURE" for item in relevant),
                    source_cycle_ids=tuple(
                        item.source_cycle_id for item in relevant
                    ),
                )
            )

        if not observations:
            fallback = allowed[0] if allowed else "reassess_without_assuming_cause"
            return ContextualStrategyChoice(
                fallback,
                "no_observed_candidate_for_exact_context",
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
            "selected_from_observed_exact_context_outcomes",
            tuple(observations),
            True,
        )


__all__ = [
    "ContextualStrategyChoice",
    "ContextualStrategySelector",
    "StrategyCandidate",
    "StrategyContext",
]
