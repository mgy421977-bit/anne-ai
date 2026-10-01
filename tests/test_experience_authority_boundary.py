"""Regression tests for the boundary between learned experience and agency authorization.

Historical experience may inform strategy selection, but it is never an authority
source and never substitutes for current factual verification.
"""

from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from anne.core.verification import FactualStatus
from anne.learning.experience_learning import Experience


def _proposal(*, authority_required: bool = False, evidence_required: bool = True) -> ActionProposal:
    return ActionProposal(
        action="synthetic-action",
        target="synthetic-target",
        reversible=True,
        risk=0.10,
        provenance=("current-source",),
        authority_required=authority_required,
        evidence_required=evidence_required,
        side_effect=authority_required,
    )


def _learned_experience(*, factual_status: str = "VERIFIED", safe_to_reuse: bool = True) -> Experience:
    return Experience(
        source_cycle_id="historical-cycle",
        outcome="SUCCESS",
        failure_class="UNKNOWN",
        strategy="historically-successful-strategy",
        lesson="Historical observation only.",
        safe_to_reuse=safe_to_reuse,
        factual_status=factual_status,
        context_key="web_research",
        context_conditions=(("freshness", "current"),),
    )


def test_verified_learned_experience_is_not_current_verification() -> None:
    experience = _learned_experience()
    result = AgencyGate().authorize(
        _proposal(),
        safety_allowed=True,
        verification_status=None,
        needs_verification=False,
    )

    assert experience.factual_status == "VERIFIED"
    assert experience.safe_to_reuse is True
    assert result.decision is ActionDecision.DENY
    assert result.reason == "evidence context is missing"


def test_learned_experience_cannot_bypass_unverified_current_evidence() -> None:
    experience = _learned_experience(factual_status="VERIFIED")
    result = AgencyGate().authorize(
        _proposal(),
        safety_allowed=True,
        verification_status=FactualStatus.UNVERIFIED,
        needs_verification=False,
    )

    assert experience.factual_status == "VERIFIED"
    assert result.decision is ActionDecision.DENY
    assert result.reason == "factual verification is not established"


def test_learned_experience_cannot_grant_authority_for_side_effect_action() -> None:
    experience = _learned_experience()
    result = AgencyGate().authorize(
        _proposal(authority_required=True),
        safety_allowed=True,
        verification_status=FactualStatus.VERIFIED,
        needs_verification=False,
    )

    assert experience.safe_to_reuse is True
    assert result.decision is ActionDecision.REVIEW
    assert result.reason == "side-effect action requires explicit authority review"
