"""Measure bounded learning guidance on real MITOS generator outputs.

This benchmark intentionally keeps the generator seed and batch size fixed.
It measures whether guidance changes mode assignment or ANNE's deterministic
evaluation result; it does not claim generation-quality improvement.
"""
from __future__ import annotations

import json

from anne.core.mitos_generation import MitosGenerationPlan
from anne.mythos.discovery import DiscoveryDrive
from anne.mythos.engine import MitosEngine
from anne.mythos.generate import generate_candidates

GOAL = "bounded discovery task"
BATCH_SIZE = 12
SEED = 17

GUIDED_PLAN = MitosGenerationPlan(
    context_key="m7-real-generator",
    modes=("association", "hypothesis", "curiosity"),
    learned=True,
)


def evaluate(candidates: list) -> dict[str, object]:
    evaluations = [DiscoveryDrive.evaluate(candidate) for candidate in candidates]
    accepted = sum(item.accepted for item in evaluations)
    return {
        "candidate_count": len(candidates),
        "accepted_count": accepted,
        "acceptance_rate": accepted / len(candidates),
        "accepted_ids": [item.candidate_id for item in evaluations if item.accepted],
    }


def run() -> dict[str, object]:
    baseline = generate_candidates(
        GOAL,
        batch_size=BATCH_SIZE,
        engine=MitosEngine(seed=SEED, mode_conditioned=True),
    )
    guided = generate_candidates(
        GOAL,
        batch_size=BATCH_SIZE,
        engine=MitosEngine(seed=SEED, mode_conditioned=True),
        generation_plan=GUIDED_PLAN,
    )

    baseline_eval = evaluate(baseline)
    guided_eval = evaluate(guided)

    baseline_modes = [candidate.mode.value for candidate in baseline]
    guided_modes = [candidate.mode.value for candidate in guided]

    return {
        "schema_version": "mitos_real_generator_effect_v01",
        "goal": GOAL,
        "batch_size": BATCH_SIZE,
        "seed": SEED,
        "baseline": {**baseline_eval, "modes": baseline_modes},
        "guided": {**guided_eval, "modes": guided_modes},
        "mode_order_changed": baseline_modes != guided_modes,
        "acceptance_count_delta": (
            guided_eval["accepted_count"] - baseline_eval["accepted_count"]
        ),
        "acceptance_rate_delta": (
            guided_eval["acceptance_rate"] - baseline_eval["acceptance_rate"]
        ),
        "discovery_value_delta": round(
            sum(candidate.discovery_value for candidate in guided) / len(guided)
            - sum(candidate.discovery_value for candidate in baseline) / len(baseline),
            4,
        ),
        "note": (
            "Implementation-level deterministic measurement over the real "
            "MitosEngine. The current generator samples evaluation fields "
            "independently of mode, so a mode-order change may leave ANNE "
            "acceptance unchanged. This is not evidence of learning quality, "
            "generalization, or real-world discovery improvement."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
