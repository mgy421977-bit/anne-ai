"""Character integrity gate for bounded ANNE learning.

The gate keeps four concerns independent: factual status, probability,
goodness, and equality. It never turns a best-available hypothesis into a
verified fact and quarantines learning that may negatively alter behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FactualStatus(str, Enum):
    VERIFIED = "VERIFIED"
    BEST_AVAILABLE = "BEST_AVAILABLE"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class CharacterAssessment:
    factual_status: FactualStatus
    probability: float
    goodness: float
    equality: float
    learning_allowed: bool
    quarantined: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "factual_status": self.factual_status.value,
            "probability": self.probability,
            "goodness": self.goodness,
            "equality": self.equality,
            "learning_allowed": self.learning_allowed,
            "quarantined": self.quarantined,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CharacterBaseline:
    """Immutable minimum behavioural baseline for automatic learning."""

    goodness: float = 0.0
    equality: float = 0.0


class CharacterIntegrityGate:
    """Evaluate learning without allowing silent negative character drift."""

    def __init__(
        self,
        baseline: CharacterBaseline | None = None,
        *,
        min_goodness: float = 0.0,
        min_equality: float = 0.0,
        negative_probability_threshold: float = 0.20,
        best_available_threshold: float = 0.50,
    ) -> None:
        self.baseline = baseline or CharacterBaseline(min_goodness, min_equality)
        self.negative_probability_threshold = self._clamp(negative_probability_threshold)
        self.best_available_threshold = self._clamp(best_available_threshold)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def assess(
        self,
        *,
        probability: float,
        goodness: float,
        equality: float,
        evidence_verified: bool = False,
        evidence_available: bool = False,
        contradiction: bool = False,
        negative_character_risk: bool = False,
    ) -> CharacterAssessment:
        """Return an auditable learning decision.

        VERIFIED requires explicit verified evidence and no contradiction.
        BEST_AVAILABLE means a candidate is strong enough to retain as a
        hypothesis, not as fact. Any character regression or material risk is
        quarantined rather than automatically learned.
        """
        p = self._clamp(probability)
        g = self._clamp(goodness)
        e = self._clamp(equality)

        if evidence_verified and not contradiction:
            factual = FactualStatus.VERIFIED
        elif evidence_available and p >= self.best_available_threshold and not contradiction:
            factual = FactualStatus.BEST_AVAILABLE
        else:
            factual = FactualStatus.INSUFFICIENT

        regression = g < self.baseline.goodness or e < self.baseline.equality
        risk = negative_character_risk or regression or (
            (self.baseline.goodness > 0 and g < self.baseline.goodness)
            or (self.baseline.equality > 0 and e < self.baseline.equality)
        )
        probabilistic_risk = risk and p >= self.negative_probability_threshold
        quarantined = risk or probabilistic_risk
        allowed = not quarantined

        if quarantined:
            reason = "Character-impacting update quarantined; human review required."
        elif factual is FactualStatus.VERIFIED:
            reason = "Verified evidence and character baseline preserved."
        elif factual is FactualStatus.BEST_AVAILABLE:
            reason = "Best available candidate retained as a hypothesis, not a fact."
        else:
            reason = "Evidence is insufficient; retain without treating as verified fact."

        return CharacterAssessment(
            factual_status=factual,
            probability=p,
            goodness=g,
            equality=e,
            learning_allowed=allowed,
            quarantined=quarantined,
            reason=reason,
        )


__all__ = [
    "CharacterAssessment",
    "CharacterBaseline",
    "CharacterIntegrityGate",
    "FactualStatus",
]
