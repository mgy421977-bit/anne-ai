"""Deterministic resource planning from bounded ANNE experience.

The planner chooses the minimum bounded local computation profile suggested by
historical experience and current MITOS observations. It does not establish
truth, authorize actions, or claim that more computation makes a hypothesis
more correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from anne.core.resource_profile import ResourceProfile


@dataclass(frozen=True)
class ResourceDecision:
    """A resource choice, explicitly separate from epistemic authority."""

    profile: ResourceProfile
    execution: str = "local"
    basis: str = "baseline"
    reason: str = "minimal bounded profile is sufficient"
    estimated_complexity: int = 1
    minimum_sufficient_capacity: int = 1


class AdaptiveResourcePlanner:
    """Select the smallest bounded profile supported by current experience."""

    _RESOURCE_MARKERS = (
        "resource",
        "budget",
        "capacity",
        "timeout",
        "compute",
        "computation",
        "iteration",
    )

    def plan(
        self,
        problem: str,
        *,
        experiences: Iterable[Any] = (),
        mitos_outcomes: Iterable[Any] = (),
        mitos_failure_classes: Mapping[str, str] | None = None,
        baseline: ResourceProfile | None = None,
    ) -> ResourceDecision:
        del problem  # Reserved for a future bounded problem-class estimator.
        base = baseline or ResourceProfile.minimal()
        capacity = max(1, base.cpu_units)
        reasons: list[str] = []
        basis: list[str] = []

        experience_rows = tuple(experiences)
        resource_failures = sum(
            1 for item in experience_rows if self._resource_related(item)
        )
        if resource_failures:
            capacity = max(capacity, min(2 ** min(resource_failures, 3), 8))
            reasons.append(f"{resource_failures} resource-related prior observation(s)")
            basis.append("historical_experience")

        outcomes = tuple(mitos_outcomes)
        informative_outcomes = tuple(
            item for item in outcomes if self._mitos_is_informative(item)
        )
        if len(informative_outcomes) >= 3:
            capacity = max(capacity, 2)
            reasons.append(
                f"{len(informative_outcomes)} informative MITOS outcomes require "
                "expanded bounded exploration"
            )
            basis.append("mitos_complexity")

        if len(outcomes) >= 6:
            capacity = max(capacity, 4)
            reasons.append("large MITOS outcome set")
            basis.append("mitos_complexity")

        failure_map = mitos_failure_classes or {}
        mapped_resource_failures = sum(
            1 for value in failure_map.values() if self._resource_text(str(value))
        )
        if mapped_resource_failures:
            capacity = max(capacity, 2)
            reasons.append(
                f"{mapped_resource_failures} MITOS resource-related failure signal(s)"
            )
            basis.append("mitos_failure_history")

        capacity = min(capacity, 8)
        profile = ResourceProfile.scaled(
            substrate=base.substrate,
            capacity=capacity,
        )
        if capacity == base.cpu_units and not reasons:
            return ResourceDecision(
                profile=profile,
                basis="baseline",
                reason="no evidence requires escalation beyond the baseline profile",
                estimated_complexity=capacity,
                minimum_sufficient_capacity=capacity,
            )

        return ResourceDecision(
            profile=profile,
            basis="+".join(dict.fromkeys(basis)) or "baseline",
            reason="; ".join(reasons),
            estimated_complexity=capacity,
            minimum_sufficient_capacity=capacity,
        )

    @classmethod
    def _resource_related(cls, item: Any) -> bool:
        if isinstance(item, Mapping):
            values = [
                str(item.get(key, ""))
                for key in ("failure_class", "strategy", "lesson", "outcome")
            ]
        else:
            values = [
                str(getattr(item, key, ""))
                for key in ("failure_class", "strategy", "lesson", "outcome")
            ]
        return cls._resource_text(" ".join(values))

    @classmethod
    def _resource_text(cls, text: str) -> bool:
        lowered = text.casefold()
        return any(marker in lowered for marker in cls._RESOURCE_MARKERS)

    @staticmethod
    def _mitos_is_informative(item: Any) -> bool:
        status = str(
            item.get("status", "")
            if isinstance(item, Mapping)
            else getattr(item, "status", "")
        ).upper()
        return status in {"TESTED", "VERIFIED", "FAILED", "INCONCLUSIVE"}


__all__ = ["AdaptiveResourcePlanner", "ResourceDecision"]
