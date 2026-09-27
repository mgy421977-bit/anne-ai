from __future__ import annotations

from collections.abc import Iterable, Sequence

from anne.learning.evidence import EvidenceItem, SupportStatus
from anne.learning.hypothesis import (
    CriticResult,
    Hypothesis,
    HypothesisCritic,
)


class EvidenceHypothesisBridge:
    """Maps ledger evidence to bounded hypothesis assessments.

    Evidence is consumed as an explicit support signal; this bridge never
    upgrades evidence or invents a semantic relation that is not recorded.
    """

    def assess(
        self,
        hypotheses: Sequence[Hypothesis],
        evidence: Iterable[EvidenceItem],
    ) -> CriticResult:
        rows: list[tuple[str, str]] = []
        for item in evidence:
            support = item.support.strip().lower()
            if support == SupportStatus.SUPPORTS.value:
                signal = "SUPPORTS"
            elif support == SupportStatus.CONTRADICTS.value:
                signal = "CONTRADICTS"
            else:
                signal = "UNCLEAR"

            hypothesis_id = self._hypothesis_id(item.claim, hypotheses)
            if hypothesis_id is not None:
                rows.append((hypothesis_id, signal))

        return HypothesisCritic().assess(hypotheses, rows)

    @staticmethod
    def _hypothesis_id(claim: str, hypotheses: Sequence[Hypothesis]) -> str | None:
        for hypothesis in hypotheses:
            if claim.strip() == hypothesis.claim.strip():
                return hypothesis.id
        return None
