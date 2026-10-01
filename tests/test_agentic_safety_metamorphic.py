"""Metamorphic regression tests for the agentic safety authorization boundary.

These tests apply controlled perturbations to the existing synthetic held-out fixture.
They do not test LLM generation or claim adversarial generalization.
"""

from __future__ import annotations

import copy
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


def _authorize(scenario: dict):
    return AgencyGate().authorize(
        _proposal(scenario["proposal"]),
        safety_allowed=scenario["safety_allowed"],
        verification_status=FactualStatus[scenario["verification_status"]],
        needs_verification=scenario["needs_verification"],
    )


def _scenario(scenario_id: str) -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(row for row in data["scenarios"] if row["id"] == scenario_id)


def test_benign_identity_perturbation_preserves_clean_allow() -> None:
    """Changing action/target labels alone must not change a clean gate decision."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["proposal"]["action"] = "renamed-synthetic-action"
    scenario["proposal"]["target"] = "different-synthetic-target"
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.ALLOW


def test_verification_downgrade_never_promotes_execution() -> None:
    """VERIFIED -> CONFLICTING must not turn an executable proposal into ALLOW."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["verification_status"] = "CONFLICTING"
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.DENY


def test_provenance_removal_never_promotes_execution() -> None:
    """Removing provenance from a verified proposal must remain fail-closed."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["proposal"]["provenance"] = []
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.DENY


def test_verification_request_never_promotes_execution() -> None:
    """A new requirement for verification must not preserve ALLOW."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["needs_verification"] = True
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.DENY


def test_safety_policy_downgrade_never_promotes_execution() -> None:
    """Safety approval -> denial must never preserve execution authority."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["safety_allowed"] = False
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.DENY


def test_risk_increase_crossing_threshold_moves_to_review() -> None:
    """Increasing risk from low to threshold must require review, not execute."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["proposal"]["risk"] = 0.50
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.REVIEW


def test_authority_and_side_effect_perturbation_requires_review() -> None:
    """Adding explicit authority and side-effect requirements must not yield ALLOW."""
    scenario = copy.deepcopy(_scenario("clean_verified_reversible"))
    baseline = _authorize(scenario)
    scenario["proposal"]["authority_required"] = True
    scenario["proposal"]["side_effect"] = True
    perturbed = _authorize(scenario)

    assert baseline.decision is ActionDecision.ALLOW
    assert perturbed.decision is ActionDecision.REVIEW


def test_unsafe_fixture_rows_remain_non_executable_under_label_changes() -> None:
    """Non-security label changes must not weaken existing unsafe boundaries."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    unsafe = [row for row in data["scenarios"] if not row["expected_executable"]]

    for scenario in unsafe:
        perturbed = copy.deepcopy(scenario)
        perturbed["proposal"]["action"] = f"renamed-{scenario['proposal']['action']}"
        perturbed["proposal"]["target"] = "different-synthetic-target"
        result = _authorize(perturbed)
        assert result.decision is not ActionDecision.ALLOW, scenario["id"]
