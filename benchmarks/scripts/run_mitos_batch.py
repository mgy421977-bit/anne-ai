#!/usr/bin/env python3
"""Run the deterministic MITOS batch-size selection protocol."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "mitos_batch_v01.json"


def select(candidates: list[dict[str, object]], batch_size: int, k: int) -> list[dict[str, object]]:
    batch = candidates[:batch_size]
    return sorted(batch, key=lambda item: (-float(item["score"]), str(item["id"])))[:k]


def run() -> dict[str, object]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    candidates = fixture["candidates"]
    protocol = fixture["protocol"]
    k = int(protocol["selection_k"])

    conditions = {
        "baseline": int(protocol["baseline_batch_size"]),
        "small": int(protocol["small_batch_size"]),
        "large": int(protocol["large_batch_size"]),
    }

    results = []
    for name, size in conditions.items():
        selected = select(candidates, size, k)
        discovery_hits = sum(1 for item in selected if item["discovery"])
        results.append(
            {
                "condition": name,
                "batch_size": size,
                "selected": [item["id"] for item in selected],
                "discovery_hits_at_k": discovery_hits,
                "discovery_rate_at_k": discovery_hits / k,
            }
        )

    baseline = results[0]["discovery_hits_at_k"]
    for row in results:
        row["discovery_lift_vs_baseline"] = row["discovery_hits_at_k"] - baseline

    return {
        "schema_version": fixture["schema_version"],
        "selection_k": k,
        "results": results,
        "note": (
            "Synthetic deterministic protocol only. Batch size is evaluated against "
            "a fixed candidate fixture; this is not evidence of real MITOS generation "
            "quality, model improvement, or generalization."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
