"""Contract tests for the held-out agentic safety authorization fixture."""

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


def test_heldout_fixture_is_declared_test_split() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["split"] == "test"
    assert len(data["scenarios"]) >= 8
    assert len({row["id"] for row in data["scenarios"]}) == len(data["scenarios"])


def test_clean_control_is_executable() -> None:
    scenario = next(
        row for row in json.loads(FIXTURE.read_text(encoding="utf-8"))["scenarios"]
        if row["id"] == "clean_verified_reversible"
    )
    result = AgencyGate().authorize(
        _proposal(scenario["proposal"]),
        safety_allowed=scenario["safety_allowed"],
        verification_status=FactualStatus[scenario["verification_status"]],
        needs_verification=scenario["needs_verification"],
    )
    assert result.decision is ActionDecision.ALLOW


def test_heldout_unsafe_scenarios_never_execute() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    unsafe = [row for row in data["scenarios"] if not row["expected_executable"]]
    assert unsafe
    for scenario in unsafe:
        result = AgencyGate().authorize(
            _proposal(scenario["proposal"]),
            safety_allowed=scenario["safety_allowed"],
            verification_status=FactualStatus[scenario["verification_status"]],
            needs_verification=scenario["needs_verification"],
        )
        assert result.decision is not ActionDecision.ALLOW, scenario["id"]


def test_heldout_categories_cover_distinct_boundaries() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    categories = {row["category"] for row in data["scenarios"]}
    assert {
        "authority_boundary",
        "memory_boundary",
        "verification_boundary",
        "provenance_boundary",
        "policy_boundary",
        "freshness_boundary",
        "risk_boundary",
    } <= categories
