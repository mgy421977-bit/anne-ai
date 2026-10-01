"""Bridge MITOS outcome records into bounded ANNE experience learning.

Only completed MITOS outcomes are converted. Hypotheses and predictions remain
discovery artifacts, and the adapter never grants authority or reusable trust.
"""

from __future__ import annotations

from anne.learning.experience_learning import Experience
from anne.mythos.experience import ExperienceRecord, ExperienceStatus


class MitosExperienceAdapter:
    """Convert explicit MITOS outcomes into non-authoritative Experience records."""

    _COMPLETED = {
        ExperienceStatus.VERIFIED,
        ExperienceStatus.FAILED,
        ExperienceStatus.INCONCLUSIVE,
    }

    def to_experience(
        self,
        record: ExperienceRecord,
        *,
        cycle_id: str | None = None,
        strategy: str = "",
        failure_class: str = "unknown",
        context_key: str = "mitos",
    ) -> Experience | None:
        if record.status not in self._COMPLETED:
            return None

        outcome = (
            "SUCCESS"
            if record.status is ExperienceStatus.VERIFIED
            else "FAILURE"
        )
        factual_status = (
            record.status.value
            if record.status is ExperienceStatus.VERIFIED
            else "UNVERIFIED"
        )
        source_cycle_id = cycle_id or record.hypothesis_id
        conditions = tuple(
            sorted(
                (str(key), str(value))
                for key, value in record.context.items()
                if str(key).strip()
            )
        )
        return Experience(
            source_cycle_id=source_cycle_id,
            outcome=outcome,
            failure_class=failure_class if outcome == "FAILURE" else "unknown",
            strategy=strategy,
            lesson=(
                "Observed MITOS outcome; this record is observational and "
                "must not be promoted to truth or authority."
            ),
            safe_to_reuse=False,
            factual_status=factual_status,
            context_key=context_key,
            context_conditions=conditions,
            parent_cycle_id=None,
            lineage=(source_cycle_id,),
        )


__all__ = ["MitosExperienceAdapter"]
