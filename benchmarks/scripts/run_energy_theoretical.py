#!/usr/bin/env python3
"""Theoretical energy model for ANNE cognitive reuse.

This is a parameterized model, not a physical energy measurement.
It compares repeated task execution against a fixed LLM reference and
accounts explicitly for ANNE's initial learning cost.

Default reference: 0.31 Wh/task (user-configurable).

Run:
    python benchmarks/scripts/run_energy_theoretical.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class Scenario:
    name: str
    repeat_ratio: float


SCENARIOS = (
    Scenario("conservative_20pct_saving", 0.80),
    Scenario("moderate_50pct_saving", 0.50),
    Scenario("strong_70pct_saving", 0.30),
    Scenario("aggressive_90pct_saving", 0.10),
)


def calculate(llm_wh: float, learn_equivalent_tasks: float, tasks: int, ratio: float) -> dict:
    learn_wh = llm_wh * learn_equivalent_tasks
    anne_repeat_wh = llm_wh * ratio
    llm_total = tasks * llm_wh
    anne_total = learn_wh + tasks * anne_repeat_wh
    saving = 1.0 - (anne_total / llm_total)
    denominator = llm_wh - anne_repeat_wh
    break_even = learn_wh / denominator if denominator > 0 else None
    return {
        "tasks": tasks,
        "llm_total_wh": round(llm_total, 6),
        "anne_learning_wh": round(learn_wh, 6),
        "anne_repeat_wh_per_task": round(anne_repeat_wh, 6),
        "anne_total_wh": round(anne_total, 6),
        "theoretical_saving_fraction": round(saving, 6),
        "theoretical_saving_percent": round(saving * 100, 3),
        "break_even_tasks": round(break_even, 3) if break_even is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-wh", type=float, default=0.31)
    parser.add_argument("--learn-equivalent-tasks", type=float, default=10.0)
    parser.add_argument("--tasks", type=int, nargs="+", default=[10, 20, 100, 1000, 10000, 100000])
    args = parser.parse_args()

    if args.llm_wh <= 0 or args.learn_equivalent_tasks < 0 or any(t <= 0 for t in args.tasks):
        parser.error("llm-wh and tasks must be positive; learn-equivalent-tasks must be non-negative")

    scenarios = []
    for scenario in SCENARIOS:
        rows = [calculate(args.llm_wh, args.learn_equivalent_tasks, n, scenario.repeat_ratio) for n in args.tasks]
        scenarios.append({
            "name": scenario.name,
            "repeat_energy_ratio": scenario.repeat_ratio,
            "rows": rows,
        })

    payload = {
        "experiment": "ANNE vs LLM Theoretical Energy Model",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_type": "parameterized_theoretical_model_not_physical_measurement",
        "reference": {
            "llm_energy_wh_per_task": args.llm_wh,
            "anne_learning_cost_equivalent_llm_tasks": args.learn_equivalent_tasks,
            "note": "Reference and ANNE ratios are assumptions; replace with measured values in hardware benchmark."
        },
        "scenarios": scenarios,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_energy_theoretical.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for scenario in scenarios:
        final = scenario["rows"][-1]
        print(f"{scenario['name']}: {final['tasks']} tasks -> LLM {final['llm_total_wh']} Wh | ANNE {final['anne_total_wh']} Wh | saving {final['theoretical_saving_percent']}% | break-even {final['break_even_tasks']} tasks")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
