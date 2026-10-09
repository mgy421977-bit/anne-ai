"""Deterministic resource planning from bounded ANNE experience.

The planner chooses the minimum bounded computation profile suggested by
historical experience and current MITOS observations. It does not establish
truth, authorize actions, or claim that more computation makes a hypothesis
more correct.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping
from typing import Any

from anne.core.resource_profile import ResourceProfile


@dataclass(frozen=True)
class ExperienceProfile:
    """Bounded aggregate of reusable runtime experience."""

    observation_count: int = 0
    resource_failure_count: int = 0
    reusable_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total else 0.0


@dataclass(frozen=True)
class ResourceDecision:
    """A resource choice, explicitly separate from epistemic authority."""

    profile: ResourceProfile
    execution: str = "local"
    basis: str = "baseline"
    reason: str = "minimal bounded profile is sufficient"
    estimated_complexity: int = 1
    minimum_sufficient_capacity: int = 1
    experience_profile: ExperienceProfile = ExperienceProfile()


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
        base = baseline or ResourceProfile.minimal()
        capacity = max(1, base.cpu_units)
        reasons: list[str] = []
        basis: list[str] = []

        experience_rows = tuple(experiences)
        profile = self._experience_profile(experience_rows)
        if profile.resource_failure_count:
            capacity = max(
                capacity,
                min(2 ** min(profile.resource_failure_count, 3), 8),
            )
            reasons.append(
                f"{profile.resource_failure_count} resource-related prior observation(s)"
            )
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

        relation_count = self._sum_numeric(outcomes, "relation_count")
        contradiction_count = self._sum_numeric(outcomes, "contradiction_count")
        candidate_count = self._max_numeric(outcomes, "candidate_count")
        if relation_count >= 4 or contradiction_count >= 2:
            capacity = max(capacity, 2)
            reasons.append(
                "epistemic relation/contradiction structure requires expanded bounded reasoning"
            )
            basis.append("epistemic_complexity")
        if relation_count >= 12 or contradiction_count >= 5 or candidate_count >= 16:
            capacity = max(capacity, 4)
            reasons.append("high bounded epistemic branching")
            basis.append("epistemic_complexity")

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

        # A complex problem should not escalate merely because it is novel:
        # only bounded structural signals above can increase capacity.
        del problem

        capacity = min(capacity, 8)
        profile_out = ResourceProfile.scaled(
            substrate=base.substrate,
            capacity=capacity,
        )
        if capacity == base.cpu_units and not reasons:
            return ResourceDecision(
                profile=profile_out,
                basis="baseline",
                reason="no evidence requires escalation beyond the baseline profile",
                estimated_complexity=capacity,
                minimum_sufficient_capacity=capacity,
                experience_profile=profile,
            )

        return ResourceDecision(
            profile=profile_out,
            basis="+".join(dict.fromkeys(basis)) or "baseline",
            reason="; ".join(reasons),
            estimated_complexity=capacity,
            minimum_sufficient_capacity=capacity,
            experience_profile=profile,
        )

    @classmethod
    def _experience_profile(cls, items: tuple[Any, ...]) -> ExperienceProfile:
        resource_failures = sum(1 for item in items if cls._resource_related(item))
        reusable = sum(
            1
            for item in items
            if bool(
                item.get("safe_to_reuse", False)
                if isinstance(item, Mapping)
                else getattr(item, "safe_to_reuse", False)
            )
        )
        successes = sum(
            1
            for item in items
            if cls._status_text(item) in {"SUCCESS", "SUCCEEDED", "VERIFIED"}
        )
        failures = sum(
            1
            for item in items
            if cls._status_text(item) in {"FAILURE", "FAILED", "ABORTED"}
        )
        return ExperienceProfile(
            observation_count=len(items),
            resource_failure_count=resource_failures,
            reusable_count=reusable,
            success_count=successes,
            failure_count=failures,
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
    def _status_text(item: Any) -> str:
        value = (
            item.get("status", item.get("outcome", ""))
            if isinstance(item, Mapping)
            else getattr(item, "status", getattr(item, "outcome", ""))
        )
        return str(value).upper()

    @classmethod
    def _mitos_is_informative(cls, item: Any) -> bool:
        return cls._status_text(item) in {
            "TESTED",
            "VERIFIED",
            "FAILED",
            "INCONCLUSIVE",
        }

    @staticmethod
    def _numeric(item: Any, key: str) -> float:
        value = item.get(key, 0) if isinstance(item, Mapping) else getattr(item, key, 0)
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _sum_numeric(cls, items: tuple[Any, ...], key: str) -> float:
        return sum(cls._numeric(item, key) for item in items)

    @classmethod
    def _max_numeric(cls, items: tuple[Any, ...], key: str) -> float:
        return max((cls._numeric(item, key) for item in items), default=0.0)


__all__ = ["AdaptiveResourcePlanner", "ExperienceProfile", "ResourceDecision"]
