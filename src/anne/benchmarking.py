"""Paired replay of frozen model outputs without feeding labels to the gates."""

from __future__ import annotations

import hashlib
import json
import math
from statistics import mean
from time import perf_counter
from typing import Any

from anne.core.decision_loop import DecisionLoop
from anne.memory.fractal_memory import FractalMemory


def summarize_pairs(pairs: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    acceptable = sum(pair["expected_acceptable"] for pair in pairs)
    unacceptable = len(pairs) - acceptable
    false_accept = sum(
        pair[condition]["accepted"] and not pair["expected_acceptable"] for pair in pairs
    )
    false_reject = sum(
        not pair[condition]["accepted"] and pair["expected_acceptable"] for pair in pairs
    )
    return {
        "n": len(pairs),
        "accepted": sum(pair[condition]["accepted"] for pair in pairs),
        "abstained": sum(pair[condition]["abstained"] for pair in pairs),
        "false_accept": false_accept,
        "false_reject": false_reject,
        "false_accept_rate": false_accept / unacceptable if unacceptable else None,
        "false_reject_rate": false_reject / acceptable if acceptable else None,
        "mean_gate_latency_ms": mean(pair[condition]["gate_latency_ms"] for pair in pairs),
        "mean_total_latency_ms": mean(pair[condition]["total_latency_ms"] for pair in pairs),
    }


def evaluate_replay(dataset: dict[str, Any]) -> dict[str, Any]:
    """Compare pass-through and ANNE using identical previously generated text.

This measures output filtering, not two independently generated agent runs.
Each sample uses fresh memory to avoid order-dependent leakage between samples.
"""
    rows = dataset.get("samples")
    if not isinstance(rows, list) or not rows:
        raise ValueError("A non-empty samples list is required")
    if dataset.get("split") not in {"development", "test"}:
        raise ValueError("Declare split as development or test")
    if not isinstance(dataset.get("model"), str) or not dataset["model"].strip():
        raise ValueError("Record the generation model, or explicitly mark synthetic data")
    if not isinstance(dataset.get("generation_settings"), dict):
        raise ValueError("Record generation_settings, including seed when available")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each sample must be an object")
        for key in ("id", "prompt", "response"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Each sample requires non-empty {key}")
        if row["id"] in seen:
            raise ValueError("Sample IDs must be unique")
        seen.add(row["id"])
        if not isinstance(row.get("expected_acceptable"), bool):
            raise ValueError("expected_acceptable must be an independently assigned boolean")
        latency = row.get("generation_latency_ms")
        if (
            isinstance(latency, bool) or not isinstance(latency, (int, float))
            or not math.isfinite(latency) or latency < 0
        ):
            raise ValueError("generation_latency_ms must be finite and non-negative")

    pairs: list[dict[str, Any]] = []
    for row in rows:
        memory = FractalMemory(":memory:")
        try:
            loop = DecisionLoop(memory=memory)
            start = perf_counter()
            decision = loop.run(row["prompt"])
            if decision.status != "ABORTED":
                decision = loop.run(row["response"])
            gate_ms = (perf_counter() - start) * 1000
        finally:
            memory.conn.close()
        accepted = decision.status == "EXECUTED" and decision.action != "HALT"
        pairs.append({
            "id": row["id"],
            "response_sha256": hashlib.sha256(row["response"].encode()).hexdigest(),
            "expected_acceptable": row["expected_acceptable"],
            "raw": {
                "accepted": True, "abstained": False, "gate_latency_ms": 0.0,
                "total_latency_ms": row["generation_latency_ms"],
            },
            "anne": {
                "accepted": accepted, "abstained": decision.verdict == "ABSTAIN",
                "gate_latency_ms": gate_ms,
                "total_latency_ms": row["generation_latency_ms"] + gate_ms,
                "verdict": decision.verdict, "factual_status": "unverified",
            },
        })
    encoded = json.dumps(dataset, ensure_ascii=False, sort_keys=True).encode()
    return {
        "schema_version": 1,
        "protocol": "frozen-response-replay-v1",
        "dataset_sha256": hashlib.sha256(encoded).hexdigest(),
        "split": dataset["split"],
        "model": dataset["model"],
        "generation_settings": dataset["generation_settings"],
        "limitations": [
            "Replay measures filtering, not end-to-end generation quality.",
            "ANLA passing does not establish factual truth.",
            "Development examples are not held-out evidence of generalization.",
            "Latency includes recorded generation plus measured gates, excluding setup.",
        ],
        "raw": summarize_pairs(pairs, "raw"),
        "anne": summarize_pairs(pairs, "anne"),
        "pairs": pairs,
    }