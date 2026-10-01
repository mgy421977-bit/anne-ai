#!/usr/bin/env python3
"""Run the deterministic next-cycle strategy handoff regression fixture."""

from __future__ import annotations

import json
from pathlib import Path

from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.learning.contextual_strategy import StrategyContext
from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyAdapter

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "learning_strategy_handoff_v01.json"


def _experience(item: dict, context_key: str) -> Experience:
    return Experience(
        source_cycle_id=item["source_cycle_id"],
        outcome=item["outcome"],
        failure_class=item["failure_class"],
        strategy=item["strategy"],
        lesson="synthetic fixture observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context_key,
    )


def run() -> dict[str, object]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    coordinator = AdaptiveLearningCoordinator()
    results = []
    for case in fixture["cases"]:
        experiences = tuple(_experience(item, case["context_key"]) for item in case["experiences"])
        current = case["current_strategy"]
        decision = StrategyAdapter().adapt(current, experiences)
        context_failure_class = experiences[-1].failure_class if experiences else "unknown"
        choice = coordinator.contextual_selector.select(
            StrategyContext(context_failure_class, case["context_key"]),
            experiences,
            (current, decision.strategy),
        )
        selected = decision.strategy if decision.action == "ABSTAIN" else choice.strategy
        observed = choice.selected_by_observation and decision.action != "ABSTAIN"
        results.append({
            "id": case["id"],
            "strategy": selected,
            "selected_by_observation": observed,
            "expected_strategy": case["expected_strategy"],
            "expected_selected_by_observation": case.get("expected_selected_by_observation", False),
            "matches": selected == case["expected_strategy"] and observed == case.get("expected_selected_by_observation", False),
        })
    passed = sum(1 for row in results if row["matches"])
    return {
        "schema_version": fixture["schema_version"],
        "case_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
