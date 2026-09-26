from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Sequence


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REJECTED = "REJECTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class Hypothesis:
    id: str
    claim: str
    rationale: str = ""
    status: HypothesisStatus = HypothesisStatus.PROPOSED


@dataclass(frozen=True)
class HypothesisAssessment:
    hypothesis_id: str
    supporting_evidence: int
    contradicting_evidence: int
    unresolved_evidence: int
    status: HypothesisStatus
    reason: str


@dataclass(frozen=True)
class CriticResult:
    assessments: tuple[HypothesisAssessment, ...]
    needs_more_research: bool
    unresolved_hypotheses: tuple[str, ...] = field(default_factory=tuple)


class HypothesisEngine:
    """Bounded hypothesis generation from an already-defined research question.

    This layer does not invent external facts. It proposes inspectable alternatives
    that can subsequently be tested against the Evidence Ledger.
    """

    def generate(self, question: str, *, max_hypotheses: int = 3) -> tuple[Hypothesis, ...]:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        if max_hypotheses < 1:
            raise ValueError("max_hypotheses must be >= 1")

        hypotheses = [
            Hypothesis("H1", question, "Direct interpretation of the research question."),
            Hypothesis("H2", f"An alternative explanation exists for: {question}",
                        "Alternative-explanation branch requiring independent evidence."),
            Hypothesis("H3", f"The available evidence may be insufficient to resolve: {question}",
                        "Uncertainty branch; tests whether the evidence base is adequate."),
        ]
        return tuple(hypotheses[:max_hypotheses])


class HypothesisCritic:
    """Scores hypotheses only from explicit evidence support signals."""

    def assess(
        self,
        hypotheses: Sequence[Hypothesis],
        evidence: Iterable[tuple[str, str]],
    ) -> CriticResult:
        evidence_rows = tuple(evidence)
        assessments: list[HypothesisAssessment] = []

        for hypothesis in hypotheses:
            support = contradiction = unresolved = 0
            for hypothesis_id, signal in evidence_rows:
                if hypothesis_id != hypothesis.id:
                    continue
                normalized = signal.strip().upper()
                if normalized == "SUPPORTS":
                    support += 1
                elif normalized == "CONTRADICTS":
                    contradiction += 1
                else:
                    unresolved += 1

            if support and contradiction:
                status = HypothesisStatus.UNRESOLVED
                reason = "Supporting and contradicting evidence coexist."
            elif contradiction and not support:
                status = HypothesisStatus.REJECTED
                reason = "Explicit contradicting evidence exists without support."
            elif support:
                status = HypothesisStatus.SUPPORTED
                reason = "Explicit supporting evidence exists without contradiction."
            else:
                status = HypothesisStatus.UNRESOLVED
                reason = "No decisive support signal is available."

            assessments.append(
                HypothesisAssessment(
                    hypothesis.id, support, contradiction, unresolved, status, reason
                )
            )

        unresolved = tuple(a.hypothesis_id for a in assessments if a.status == HypothesisStatus.UNRESOLVED)
        return CriticResult(tuple(assessments), bool(unresolved), unresolved)
