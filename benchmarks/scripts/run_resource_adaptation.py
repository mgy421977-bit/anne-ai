#!/usr/bin/env python3
"""Resource-adaptive ANNE benchmark simulation.

Models how a cognitive runtime can discover a hardware profile, select a
resource strategy, execute the same workload, and re-regulate when resources
change. This is a deterministic simulation, not a hardware power measurement.

Run:
    python benchmarks/scripts/run_resource_adaptation.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"


@dataclass(frozen=True)
class Environment:
    name: str
    cpu_cores: int
    ram_gb: float
    gpu: bool
    gpu_memory_gb: float
    storage_gb: float


@dataclass(frozen=True)
class Strategy:
    name: str
    parallelism: int
    memory_reuse: float
    compute_factor: float


ENVIRONMENTS = (
    Environment("ENV-A-CPU-4GB", 4, 4.0, False, 0.0, 128.0),
    Environment("ENV-B-GPU-16GB", 8, 16.0, True, 8.0, 512.0),
    Environment("ENV-C-GPU-64GB", 16, 64.0, True, 48.0, 2048.0),
)


def discover(env: Environment) -> dict:
    return asdict(env)


def select_strategy(env: Environment) -> Strategy:
    if env.gpu and env.gpu_memory_gb >= 32 and env.ram_gb >= 32:
        return Strategy("high_memory_parallel_reuse", 8, 0.90, 0.70)
    if env.gpu and env.ram_gb >= 16:
        return Strategy("gpu_balanced_reuse", 4, 0.70, 0.85)
    return Strategy("cpu_memory_saver", 1, 0.50, 1.15)


def simulate_task(env: Environment, strategy: Strategy, base_compute_units: float) -> dict:
    effective_compute = base_compute_units * strategy.compute_factor
    # A simple deterministic proxy: more parallelism reduces wall-clock time,
    # while the reuse factor reduces repeated cognitive reconstruction work.
    latency_units = effective_compute / strategy.parallelism
    reusable_work = effective_compute * (1.0 - strategy.memory_reuse)
    return {
        "effective_compute_units": round(effective_compute, 6),
        "latency_units": round(latency_units, 6),
        "reusable_work_units": round(reusable_work, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=100)
    parser.add_argument("--base-compute", type=float, default=100.0)
    args = parser.parse_args()
    if args.tasks <= 0 or args.base_compute <= 0:
        parser.error("tasks and base-compute must be positive")

    rows = []
    for env in ENVIRONMENTS:
        strategy = select_strategy(env)
        first = simulate_task(env, strategy, args.base_compute)
        repeated = simulate_task(env, strategy, args.base_compute * (1.0 - strategy.memory_reuse))
        rows.append({
            "environment": discover(env),
            "selected_strategy": asdict(strategy),
            "first_task": first,
            "repeated_task": repeated,
            "tasks": args.tasks,
            "regulation_policy": "reuse learned structures; re-profile if resource availability changes",
        })

    payload = {
        "experiment": "ANNE Resource-Adaptive Runtime Simulation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_type": "deterministic resource simulation; not physical benchmark",
        "workload": {"tasks": args.tasks, "base_compute_units": args.base_compute},
        "adaptation_loop": ["INSTALL", "DISCOVER", "PROFILE", "CONNECT", "CALIBRATE", "OPTIMIZE", "RUN", "MONITOR", "RE-REGULATE"],
        "environments": rows,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_resource_adaptation.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for row in rows:
        print(f"{row['environment']['name']}: {row['selected_strategy']['name']} | first compute {row['first_task']['effective_compute_units']} | repeated compute {row['repeated_task']['effective_compute_units']}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
