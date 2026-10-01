"""Bounded controller for metacognitive next-step signals.

Metacognition observes a completed process. This controller is the separate,
bounded decision layer that may translate an explicit metacognitive signal into
review or research guidance without granting authority or executing tools.
"""

from __future__ import annotations

from anne.learning.critic_loop import LoopDecision
from anne.learning.metacognition import MetacognitiveAssessment


class MetacognitiveController:
    """Translate explicit metacognitive gaps into bounded loop guidance."""

    def apply(
        self,
        assessment: MetacognitiveAssessment,
        decision: LoopDecision,
    ) -> LoopDecision:
        if assessment.requires_review:
            if assessment.research_required and decision.research_allowed:
                return LoopDecision(
                    action="RESEARCH",
                    reason=assessment.research_reason
                    or "Metacognitive assessment requires evidence reassessment.",
                    research_allowed=True,
                )
            if not assessment.research_required:
                return LoopDecision(
                    action="REVIEW",
                    reason=(
                        assessment.research_reason
                        or "Metacognitive assessment requires process review."
                    ),
                    research_allowed=False,
                )

        return decision


__all__ = ["MetacognitiveController"]
