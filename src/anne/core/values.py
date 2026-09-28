"""ANNE Core values: operational goodness and equality principles.

The core is intentionally small and deterministic. It does not claim that a
numeric score is a complete moral theory; it provides an inspectable decision
boundary that higher-level cognition can use and test.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CoreDecision(StrEnum):
    PROCEED = "PROCEED"
    SEPARATE = "SEPARATE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class CoreResolution:
    """Result of applying the ANNE Core principles to an explicit assessment."""

    decision: CoreDecision
    goodness: float
    equality: float
    principles_conflict: bool
    parties_conflict: bool
    common_solution: bool
    reason: str


class ANNECore:
    """Deterministic first-pass implementation of ANNE's two core principles.

    Principle 1 — GOODNESS:
    protect a being's existence, integrity, safety, freedom and opportunity
    to develop; avoid actions whose essential effect is unnecessary harm.

    Principle 2 — EQUALITY:
    treat beings as equal in basic value and equal in their entitlement to
    basic resources; do not introduce arbitrary preference.

    Conflict rule:
    when the explicit assessment says the principles cannot both be satisfied,
    GOODNESS has priority.

    Separation rule:
    a conflict between parties does not require a common outcome. If a common
    solution would harm one or both parties, separate solutions are preferred.
    """

    GOODNESS_DEFINITION = (
        "Protect existence, integrity, safety, freedom and opportunity to develop; "
        "avoid unnecessary harm."
    )
    EQUALITY_DEFINITION = (
        "Treat beings as equal in basic value and in their entitlement to basic "
        "resources; no arbitrary preference."
    )
    GOODNESS_PRIORITY = "When goodness and equality conflict, goodness has priority."
    SEPARATION_RULE = (
        "When no common solution can protect the parties, seek separate solutions "
        "for each party rather than forcing a common outcome."
    )

    def resolve(
        self,
        *,
        goodness: float,
        equality: float,
        principles_conflict: bool = False,
        parties_conflict: bool = False,
        common_solution: bool = True,
    ) -> CoreResolution:
        """Apply the core rules to explicit, bounded assessment inputs."""
        self._validate_score("goodness", goodness)
        self._validate_score("equality", equality)

        if goodness <= 0.0:
            return CoreResolution(
                CoreDecision.BLOCK,
                goodness,
                equality,
                principles_conflict,
                parties_conflict,
                common_solution,
                "The proposed path is incompatible with the goodness principle.",
            )

        if parties_conflict and not common_solution:
            return CoreResolution(
                CoreDecision.SEPARATE,
                goodness,
                equality,
                principles_conflict,
                parties_conflict,
                common_solution,
                "A common solution is not compatible with the parties' well-being; "
                "evaluate independent solutions.",
            )

        if principles_conflict:
            return CoreResolution(
                CoreDecision.PROCEED,
                goodness,
                equality,
                principles_conflict,
                parties_conflict,
                common_solution,
                "Principles conflict; goodness has priority under the ANNE Core.",
            )

        if equality <= 0.0:
            return CoreResolution(
                CoreDecision.BLOCK,
                goodness,
                equality,
                principles_conflict,
                parties_conflict,
                common_solution,
                "The proposed path violates the equality principle.",
            )

        return CoreResolution(
            CoreDecision.PROCEED,
            goodness,
            equality,
            principles_conflict,
            parties_conflict,
            common_solution,
            "Goodness and equality are both satisfied by the explicit assessment.",
        )

    @staticmethod
    def _validate_score(name: str, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")


__all__ = ["ANNECore", "CoreDecision", "CoreResolution"]
