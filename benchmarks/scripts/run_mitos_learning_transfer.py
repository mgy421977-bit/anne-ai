"""Small reproducible benchmark for bounded MITOS learning transfer."""

from __future__ import annotations

import json
from pathlib import Path

from anne.core.mitos_experience import ExperienceStatus, MitosExperience
from anne.core.mitos_feedback import apply_feedback
from anne.core.mitos_learning import derive_learning_guidance
from anne.core.mitos_generation import plan_generation_modes


MODES = ("EXPLORE", "COMBINE", "INVERT", "SIMULATE")


def _experience(context: str, mode: str, status: ExperienceStatus) -> MitosExperience:
    item = MitosExperience(
        hypothesis=f"{mode} hypothesis",
        prediction=f"{mode} prediction",
        predicted_probability=0.4,
        confidence=0.3,
        novelty=0.8,
        testability=0.9,
        expected_benefit=0.7,
        harm_risk=0.0,
        test_cost=0.1,
        status=ExperienceStatus.PREDICTION,
        context_key=context,
        generation_mode=mode,
    )
    apply_feedback(
        item,
        observation={"mode": mode},
        outcome={"status": status.value},
        status=status,
        prediction_error=0.1,
    )
    return item


def run_benchmark() -> dict[str, object]:
    context = "benchmark:energy"
    prior = [
        _experience(context, "COMBINE", ExperienceStatus.VERIFIED),
        _experience(context, "COMBINE", ExperienceStatus.VERIFIED),
        _experience(context, "INVERT", ExperienceStatus.FAILED),
        _experience("other-context", "SIMULATE", ExperienceStatus.VERIFIED),
    ]

    guidance = derive_learning_guidance(prior, context_key=context)
    baseline = plan_generation_modes(MODES)
    learned = plan_generation_modes(MODES, guidance=guidance)

    return {
        "benchmark": "mitos_learning_transfer_v0.1",
        "context": context,
        "prior_completed_experiences": len(prior),
        "matched_experiences": guidance.sample_size,
        "baseline_modes": list(baseline.modes),
        "learned_modes": list(learned.modes),
        "ordering_changed": learned.modes != baseline.modes,
        "preferred_modes": list(guidance.preferred_modes),
        "avoid_modes": list(guidance.avoid_modes),
        "cross_context_isolated": guidance.sample_size == 3,
        "execution_authority": False,
        "note": "Synthetic scaffold; demonstrates transfer mechanics, not generation-quality improvement.",
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
