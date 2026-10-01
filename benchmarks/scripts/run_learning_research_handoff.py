#!/usr/bin/env python3
"""Deterministic replay for ANNE learning/research handoff contracts.

This benchmark measures bounded strategy adaptation and derived-research learning
boundaries. It does not measure model intelligence, generalization, or security.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from anne.core.trace import CycleTrace
from anne.core.verification import FactualStatus, VerificationResult
from anne.learning.derived_research_executor import DerivedResearchResult
from anne.learning.derived_research_learning import DerivedResearchLearningAdapter
from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyAdapter

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "learning_research_handoff_v01.json"


def experience(cycle: str, failure_class: str, strategy: str, context: str = "task-a") -> Experience:
    return Experience(
        source_cycle_id=cycle,
        outcome="FAILURE",
        failure_class=failure_class,
        strategy=strategy,
        lesson="synthetic benchmark observation",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key=context,
        context_conditions=(("mode", "research"),),
    )


def strategy_rows() -> list[dict]:
    adapter = StrategyAdapter()
    rows = [
        ("no_history", (), "research"),
        ("single_failure", (experience("s1", "evidence_gap", "research"),), "research"),
        (
            "repeated_same_failure",
            (
                experience("s1", "evidence_gap", "research"),
                experience("s2", "evidence_gap", "research"),
            ),
            "research",
        ),
        (
            "mixed_failure_classes",
            (
                experience("s1", "evidence_gap", "research"),
                experience("s2", "semantic", "research"),
            ),
            "research",
        ),
        (
            "cross_context_isolation",
            (experience("s1", "evidence_gap", "research", context="task-b"),),
            "research",
        ),
    ]
    output = []
    for scenario_id, experiences, current in rows:
        decision = adapter.adapt(current, experiences)
        output.append({
            "id": scenario_id,
            "action": decision.action,
            "strategy": decision.strategy,
            "source_cycle_ids": list(decision.source_cycle_ids),
        })
    return output


def derived_row(scenario_id: str, status: FactualStatus) -> dict:
    result = DerivedResearchResult(
        plan_question="synthetic derived question",
        evidence=(),
        queries_used=1,
        sources_used=2,
        stopped_reason="plan_exhausted",
    )
    verification = VerificationResult(
        status=status,
        sources=("synthetic_source_A", "synthetic_source_B"),
        reason="synthetic benchmark verification",
    )
    trace = DerivedResearchLearningAdapter().to_trace(
        result,
        (verification,),
        cycle_id=f"benchmark:{scenario_id}",
        strategy="research",
    )
    return {
        "id": scenario_id,
        "factual_status": trace.verification["verification_status"],
        "safe_to_reuse": False,
        "stage_trace": list(trace.stage_trace),
    }


def main() -> int:
    dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != 1 or dataset.get("split") != "test":
        raise ValueError("Fixture must be schema_version=1 and split=test")

    rows = strategy_rows()
    rows.append(derived_row("verified_learning_reuse_boundary", FactualStatus.VERIFIED))
    rows.append(derived_row("conflicting_learning_reuse_boundary", FactualStatus.CONFLICTING))

    expected = {item["id"]: item["expected"] for item in dataset["scenarios"]}
    mismatches = []
    for row in rows:
        target = expected[row["id"]]
        for key, value in target.items():
            if row.get(key) != value:
                mismatches.append({"id": row["id"], "field": key, "expected": value, "actual": row.get(key)})

    payload = {
        "protocol": "learning-research-handoff-v1",
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "split": dataset["split"],
        "timestamp": datetime.now(UTC).isoformat(),
        "definition": dataset["definition"],
        "non_claims": dataset["non_claims"],
        "n": len(rows),
        "passed": len(mismatches) == 0,
        "mismatches": mismatches,
        "pairs": rows,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
