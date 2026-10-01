#!/usr/bin/env python3
"""Deterministic replay for the MITOS -> bounded strategy-learning handoff."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.mythos.experience import ExperienceRecord, ExperienceStatus

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "mitos_strategy_learning_v01.json"


def failed_trace(context: dict[str, str]) -> CycleTrace:
    return CycleTrace(
        cycle_id="current-cycle",
        status="FAILED",
        stop_reason="evidence_gap",
        intent={"requires_evidence": True},
        learning={
            "context": {
                "key": "mitos",
                "conditions": context,
            }
        },
    )


def mitos_record(hypothesis_id: str, context: dict[str, str]) -> ExperienceRecord:
    return ExperienceRecord(
        hypothesis_id=hypothesis_id,
        goal="bounded test",
        claim="synthetic claim",
        status=ExperienceStatus.FAILED,
        context=context,
    )


def run_case(case_id: str, context: dict[str, str]) -> dict:
    result = AdaptiveLearningCoordinator().observe(
        failed_trace(context),
        strategy="bounded_test",
        mitos_outcomes=(
            mitos_record("m1", {"mode": context["mode"]}),
            mitos_record("m2", {"mode": context["mode"]}),
        ),
        mitos_failure_classes={"m1": "evidence_gap", "m2": "evidence_gap"},
    )
    return {
        "id": case_id,
        "action": result.strategy.action,
        "strategy": result.strategy.strategy,
        "source_cycle_ids": list(result.strategy.source_cycle_ids),
    }


def main() -> int:
    dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = [
        run_case("repeated_same_context", {"mode": "research"}),
        run_case("repeated_cross_context", {"mode": "production"}),
    ]
    expected = {item["id"]: item["expected"] for item in dataset["scenarios"]}
    mismatches = []
    for row in rows:
        target = expected[row["id"]]
        for key, value in target.items():
            if row.get(key) != value:
                mismatches.append(
                    {
                        "id": row["id"],
                        "field": key,
                        "expected": value,
                        "actual": row.get(key),
                    }
                )

    payload = {
        "protocol": "mitos-strategy-learning-v1",
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
