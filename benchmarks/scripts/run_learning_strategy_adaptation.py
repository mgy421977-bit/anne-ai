#!/usr/bin/env python3
"""Run the deterministic strategy-adaptation learning regression fixture."""

from __future__ import annotations

import json
from pathlib import Path

from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyAdapter

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "learning_strategy_adaptation_v01.json"


def run() -> dict[str, object]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    adapter = StrategyAdapter()
    results = []

    for case in fixture["cases"]:
        experiences = tuple(Experience(
            source_cycle_id=item["source_cycle_id"],
            outcome=item["outcome"],
            failure_class=item["failure_class"],
            strategy=item["strategy"],
            lesson="synthetic fixture observation",
            safe_to_reuse=False,
            factual_status="UNVERIFIED",
        ) for item in case["experiences"])
        decision = adapter.adapt(case["current_strategy"], experiences)
        results.append({
            "id": case["id"],
            "action": decision.action,
            "strategy": decision.strategy,
            "expected_action": case["expected_action"],
            "expected_strategy": case["expected_strategy"],
            "matches": (
                decision.action == case["expected_action"]
                and decision.strategy == case["expected_strategy"]
            ),
        })

    passed = sum(1 for row in results if row["matches"])
    repeated = [row for row in results if row["id"] == "repeated_same_failure"]
    safety = [row for row in results if row["id"] == "safety_failure"]
    return {
        "schema_version": fixture["schema_version"],
        "case_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "strategy_change_rate_on_repeated_failure": (
            1.0 if repeated and repeated[0]["action"] == "CHANGE" else 0.0
        ),
        "unsafe_strategy_change_rate": (
            0.0 if safety and safety[0]["action"] == "ABSTAIN" else 1.0
        ),
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
