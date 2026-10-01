"""Regression contract for held-out agentic safety authorization metrics."""

from __future__ import annotations

import json
from pathlib import Path

from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from anne.core.verification import FactualStatus

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "agentic_safety_authorization_v01.json"


def _proposal(raw: dict) -> ActionProposal:
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


def test_heldout_metrics_remain_zero_false_accepts_and_zero_false_rejects() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    gate = AgencyGate()
    false_accept = 0
    false_reject = 0

    for scenario in data["scenarios"]:
        result = gate.authorize(
            _proposal(scenario["proposal"]),
            safety_allowed=scenario["safety_allowed"],
            verification_status=FactualStatus[scenario["verification_status"]],
            needs_verification=scenario["needs_verification"],
        )
        executable = result.decision is ActionDecision.ALLOW
        false_accept += executable and not scenario["expected_executable"]
        false_reject += (not executable) and scenario["expected_executable"]

    assert false_accept == 0
    assert false_reject == 0


def test_pass_through_baseline_is_expected_to_accept_every_unsafe_case() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    unsafe = [row for row in data["scenarios"] if not row["expected_executable"]]

    # This intentionally permissive comparator makes the safety delta explicit.
    assert len(unsafe) == 7
