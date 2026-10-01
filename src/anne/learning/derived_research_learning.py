"""Convert bounded derived-research verification into a learning observation.

The adapter records the outcome of the verification handoff as bounded
experience. It does not create authority, truth beyond the verifier result,
or permission to execute an action.
"""

from __future__ import annotations

from anne.core.trace import CycleTrace
from anne.core.verification import FactualStatus, VerificationResult
from anne.learning.derived_research_executor import DerivedResearchResult
from anne.learning.experience_learning import Experience


class DerivedResearchLearningAdapter:
    """Turn one derived-research verification cycle into an observed trace."""

    def to_trace(
        self,
        result: DerivedResearchResult,
        verifications: tuple[VerificationResult, ...],
        *,
        cycle_id: str,
        strategy: str = "research",
        parent_experience: Experience | None = None,
    ) -> CycleTrace:
        statuses = tuple(verification.status for verification in verifications)

        if statuses and all(status is FactualStatus.VERIFIED for status in statuses):
            status = "SUCCESS"
            stop_reason = "derived_research_verified"
            decision_status = "VERIFIED"
        elif FactualStatus.CONFLICTING in statuses:
            status = "BOUNDED"
            stop_reason = "derived_research_conflict"
            decision_status = "CONFLICTING"
        elif FactualStatus.REFUTED in statuses:
            status = "BOUNDED"
            stop_reason = "derived_research_refuted"
            decision_status = "REFUTED"
        elif FactualStatus.UNVERIFIED in statuses or not statuses:
            status = "BOUNDED"
            stop_reason = "derived_research_unverified"
            decision_status = "UNVERIFIED"
        else:
            status = "BOUNDED"
            stop_reason = "derived_research_insufficient_evidence"
            decision_status = "UNVERIFIED"

        sources = tuple(
            sorted(
                {
                    source
                    for verification in verifications
                    for source in verification.sources
                }
            )
        )
        verification = {
            "verification_status": decision_status,
            "verification_sources": sources,
            "verification_reason": "Derived research independently verified before learning handoff.",
        }

        learning: dict[str, object] = {"strategy": strategy}
        parent_cycle_id = None
        lineage: tuple[str, ...] = (cycle_id,)
        if parent_experience is not None:
            parent_cycle_id = parent_experience.source_cycle_id
            lineage = (*parent_experience.lineage, cycle_id)
            if parent_experience.context_key or parent_experience.context_conditions:
                learning["context"] = {
                    "key": parent_experience.context_key,
                    "conditions": dict(parent_experience.context_conditions),
                }

        return CycleTrace(
            cycle_id=cycle_id,
            parent_cycle_id=parent_cycle_id,
            lineage=lineage,
            status=status,
            stage_trace=("DERIVED_RESEARCH", "VERIFICATION", "LEARNING"),
            stop_reason=stop_reason,
            verification=verification,
            decision={
                "status": decision_status,
                "strategy": strategy,
                "plan_question": result.plan_question,
                "queries_used": result.queries_used,
                "sources_used": result.sources_used,
            },
            learning=learning,
        )


__all__ = ["DerivedResearchLearningAdapter"]
