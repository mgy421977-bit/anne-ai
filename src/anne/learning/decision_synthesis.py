from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from anne.learning.hypothesis import CriticResult, HypothesisAssessment, HypothesisStatus


class SynthesisStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    MULTIPLE_SUPPORTED = "MULTIPLE_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECTED_WITH_ALTERNATIVES = "REJECTED_WITH_ALTERNATIVES"


@dataclass(frozen=True)
class DecisionSynthesis:
    """Deterministic synthesis of hypothesis assessments.

    This layer summarizes the current cognitive state. It never invents
    evidence, ranks hypotheses, or suppresses unresolved alternatives.
    """

    status: SynthesisStatus
    supported_hypotheses: tuple[str, ...]
    unresolved_hypotheses: tuple[str, ...]
    rejected_hypotheses: tuple[str, ...]
    reason: str

    @property
    def is_ambiguous(self) -> bool:
        return self.status in {
            SynthesisStatus.MULTIPLE_SUPPORTED,
            SynthesisStatus.CONFLICTING,
            SynthesisStatus.INSUFFICIENT_EVIDENCE,
            SynthesisStatus.REJECTED_WITH_ALTERNATIVES,
        }


class DecisionSynthesizer:
    """Convert explicit hypothesis assessments into a non-collapsing result."""

    def synthesize(self, critic: CriticResult) -> DecisionSynthesis:
        assessments: Sequence[HypothesisAssessment] = critic.assessments

        supported = tuple(
            a.hypothesis_id
            for a in assessments
            if a.status == HypothesisStatus.SUPPORTED
        )
        unresolved = tuple(
            a.hypothesis_id
            for a in assessments
            if a.status == HypothesisStatus.UNRESOLVED
        )
        rejected = tuple(
            a.hypothesis_id
            for a in assessments
            if a.status == HypothesisStatus.REJECTED
        )

        has_internal_conflict = any(
            a.supporting_evidence > 0 and a.contradicting_evidence > 0
            for a in assessments
        )
        if has_internal_conflict:
            return DecisionSynthesis(
                SynthesisStatus.CONFLICTING,
                supported,
                unresolved,
                rejected,
                "Supporting and contradicting evidence coexist for at least one hypothesis.",
            )

        if len(supported) > 1:
            return DecisionSynthesis(
                SynthesisStatus.MULTIPLE_SUPPORTED,
                supported,
                unresolved,
                rejected,
                "Multiple hypotheses have explicit supporting evidence; none is suppressed.",
            )

        if len(supported) == 1:
            return DecisionSynthesis(
                SynthesisStatus.SUPPORTED,
                supported,
                unresolved,
                rejected,
                "One hypothesis has explicit supporting evidence without internal contradiction.",
            )

        if rejected and unresolved:
            return DecisionSynthesis(
                SynthesisStatus.REJECTED_WITH_ALTERNATIVES,
                supported,
                unresolved,
                rejected,
                "A hypothesis is rejected while one or more alternatives remain unresolved.",
            )

        return DecisionSynthesis(
            SynthesisStatus.INSUFFICIENT_EVIDENCE,
            supported,
            unresolved,
            rejected,
            "No hypothesis has decisive supporting evidence.",
        )


__all__ = ["DecisionSynthesis", "DecisionSynthesizer", "SynthesisStatus"]
