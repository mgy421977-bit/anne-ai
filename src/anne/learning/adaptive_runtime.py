"""Bounded runtime feedback loop for ANNE's adaptive learning layer."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.trace import CycleTrace
from anne.runtime import AnneRuntime
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator, AdaptiveLearningResult
from anne.learning.experience_learning import Experience


@dataclass(frozen=True)
class AdaptiveRuntimeResult:
    """One runtime cycle plus its bounded learning observation."""

    decision: object
    learning: AdaptiveLearningResult
    next_strategy: str

    @property
    def trace(self) -> CycleTrace:
        return self.learning.trace


class AdaptiveRuntimeController:
    """Run bounded cycles and carry only observed strategy guidance forward."""

    def __init__(
        self,
        runtime: AnneRuntime,
        *,
        coordinator: AdaptiveLearningCoordinator | None = None,
        initial_strategy: str = "research",
        max_experiences: int = 64,
    ) -> None:
        if max_experiences < 1:
            raise ValueError("max_experiences must be positive")
        self.runtime = runtime
        self.coordinator = coordinator or AdaptiveLearningCoordinator()
        self.current_strategy = initial_strategy
        self.max_experiences = max_experiences
        self._experiences: tuple[Experience, ...] = ()

    @property
    def experiences(self) -> tuple[Experience, ...]:
        return self._experiences

    def run(
        self,
        text: str,
        *,
        learning_context: dict[str, object] | None = None,
    ) -> AdaptiveRuntimeResult:
        decision = self.runtime.run(
            text,
            learning_context=learning_context,
            strategy=self.current_strategy,
        )
        if decision.trace is None:
            raise RuntimeError("runtime decision did not produce a canonical trace")

        learning = self.coordinator.observe(
            decision.trace,
            strategy=self.current_strategy,
            prior_experiences=self._experiences,
        )
        prior_same_strategy_failures = sum(
            item.outcome == "FAILURE" and item.strategy == self.current_strategy
            for item in self._experiences
        )
        # StrategyAdapter may propose a change after two observations, but the
        # runtime applies it only after three total same-strategy failures.
        # This separates a suggestion from the policy that activates it.
        if not (
            learning.strategy.action == "CHANGE"
            and prior_same_strategy_failures < 2
        ):
            self.current_strategy = learning.strategy.strategy
        self._experiences = (
            *self._experiences,
            learning.experience,
        )[-self.max_experiences :]
        return AdaptiveRuntimeResult(
            decision=decision,
            learning=learning,
            next_strategy=self.current_strategy,
        )


__all__ = ["AdaptiveRuntimeController", "AdaptiveRuntimeResult"]
