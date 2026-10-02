#!/usr/bin/env python3
"""Run the deterministic MITOS learning guidance replay fixture."""

from __future__ import annotations

import json
from pathlib import Path

from anne.core.mitos_experience import ExperienceStatus, MitosExperience
from anne.core.mitos_feedback import apply_feedback
from anne.core.mitos_generation import plan_generation_modes
from anne.core.mitos_learning import derive_learning_guidance

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "mitos_learning_v01.json"


def make_experience(
    *,
    context_key: str,
    generation_mode: str,
    status: ExperienceStatus,
) -> MitosExperience:
    item = MitosExperience(
        hypothesis=f"synthetic-{generation_mode}",
        prediction=f"prediction-{generation_mode}",
        predicted_probability=0.4,
        confidence=0.3,
        novelty=0.8,
        testability=0.9,
        expected_benefit=0.7,
        harm_risk=0.0,
        test_cost=0.1,
        status=ExperienceStatus.PREDICTION,
        context_key=context_key,
        generation_mode=generation_mode,
    )
    apply_feedback(
        item,
        observation="synthetic observation",
        outcome="synthetic outcome",
        status=status,
        prediction_error=0.1,
    )
    return item


def run() -> dict[str, object]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    results = []

    for case in fixture["cases"]:
        experiences = [
            make_experience(
                context_key=item.get("experience_context", case["context_key"]),
                generation_mode=item["generation_mode"],
                status=ExperienceStatus(item["status"]),
            )
            for item in case["experiences"]
        ]
        guidance = derive_learning_guidance(
            experiences,
            context_key=case["context_key"],
        )
        plan = plan_generation_modes(case["modes"], guidance=guidance)
        results.append(
            {
                "id": case["id"],
                "modes": list(plan.modes),
                "expected_modes": case["expected_modes"],
                "learned": plan.learned,
                "expected_learned": case["expected_learned"],
                "matches": (
                    list(plan.modes) == case["expected_modes"]
                    and plan.learned == case["expected_learned"]
                ),
            }
        )

    passed = sum(1 for row in results if row["matches"])
    changed = sum(1 for row in results if row["learned"])
    return {
        "schema_version": fixture["schema_version"],
        "case_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "generation_plan_change_rate": changed / len(results) if results else 0.0,
        "note": "Synthetic deterministic learning contract only; not evidence of general model learning.",
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
