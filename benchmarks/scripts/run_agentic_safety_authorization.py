#!/usr/bin/env python3
"""Deterministic held-out authorization replay: pass-through vs ANNE AgencyGate.

This protocol compares a permissive baseline with ANNE's independent agency
boundary using a synthetic, non-harmful fixture. It measures authorization
outcomes, not model quality, jailbreak resistance, or production security.

    python benchmarks/scripts/run_agentic_safety_authorization.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from anne.core.verification import FactualStatus

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks" / "agentic_safety_authorization_v01.json"


def build_proposal(raw: dict) -> ActionProposal:
    return ActionProposal(
        action=raw["action"],
        target="synthetic-test-target",
        reversible=raw["reversible"],
        risk=raw["risk"],
        provenance=tuple(raw["provenance"]),
        authority_required=raw["authority_required"],
        evidence_required=raw["evidence_required"],
        side_effect=raw["side_effect"],
    )


def anne_outcome(scenario: dict) -> dict:
    result = AgencyGate().authorize(
        build_proposal(scenario["proposal"]),
        safety_allowed=scenario["safety_allowed"],
        verification_status=FactualStatus[scenario["verification_status"]],
        needs_verification=scenario["needs_verification"],
    )
    executable = result.decision is ActionDecision.ALLOW
    return {
        "decision": result.decision.name,
        "executable": executable,
        "false_accept": executable and not scenario["expected_executable"],
        "false_reject": (not executable) and scenario["expected_executable"],
    }


def baseline_outcome(scenario: dict) -> dict:
    # Intentionally permissive comparator: every proposed action is treated
    # as executable. This is a baseline, not a production-agent model.
    executable = True
    return {
        "decision": "PASS_THROUGH",
        "executable": executable,
        "false_accept": executable and not scenario["expected_executable"],
        "false_reject": False,
    }


def summarize(rows: list[dict], key: str) -> dict:
    unsafe = sum(not row["expected_executable"] for row in rows)
    safe = len(rows) - unsafe
    false_accept = sum(row[key]["false_accept"] for row in rows)
    false_reject = sum(row[key]["false_reject"] for row in rows)
    return {
        "n": len(rows),
        "executable": sum(row[key]["executable"] for row in rows),
        "review_or_deny": sum(not row[key]["executable"] for row in rows),
        "false_accept": false_accept,
        "false_reject": false_reject,
        "unauthorized_action_rate": false_accept / unsafe if unsafe else None,
        "false_reject_rate": false_reject / safe if safe else None,
    }


def main() -> int:
    dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if dataset.get("schema_version") != 1 or dataset.get("split") != "test":
        raise ValueError("Fixture must be schema_version=1 and split=test")

    rows = []
    for scenario in dataset["scenarios"]:
        rows.append({
            "id": scenario["id"],
            "category": scenario["category"],
            "expected_executable": scenario["expected_executable"],
            "baseline": baseline_outcome(scenario),
            "anne": anne_outcome(scenario),
        })

    encoded = FIXTURE.read_bytes()
    payload = {
        "protocol": "agentic-safety-authorization-v1",
        "fixture_sha256": hashlib.sha256(encoded).hexdigest(),
        "split": dataset["split"],
        "timestamp": datetime.now(UTC).isoformat(),
        "definition": dataset["definition"],
        "non_claims": dataset["non_claims"],
        "baseline": summarize(rows, "baseline"),
        "anne": summarize(rows, "anne"),
        "pairs": rows,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
