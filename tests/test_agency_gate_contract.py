from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from anne.core.cognitive_cycle import CognitiveCycle, CycleStatus
from anne.core.verification import FactualStatus


def proposal() -> ActionProposal:
    return ActionProposal(
        "external-action",
        risk=0.10,
        provenance=("source_A",),
    )


def test_verified_clean_authorized_policy_allows():
    result = AgencyGate().authorize(
        proposal(),
        safety_allowed=True,
        verification_status=FactualStatus.VERIFIED,
        needs_verification=False,
    )
    assert result.decision is ActionDecision.ALLOW


def test_unverified_denies():
    result = AgencyGate().authorize(
        proposal(),
        safety_allowed=True,
        verification_status=FactualStatus.UNVERIFIED,
    )
    assert result.decision is ActionDecision.DENY


def test_conflicting_denies():
    result = AgencyGate().authorize(
        proposal(),
        safety_allowed=True,
        verification_status=FactualStatus.CONFLICTING,
    )
    assert result.decision is ActionDecision.DENY


def test_metacognitive_verification_request_denies():
    result = AgencyGate().authorize(
        proposal(),
        safety_allowed=True,
        verification_status=FactualStatus.VERIFIED,
        needs_verification=True,
    )
    assert result.decision is ActionDecision.DENY


def test_safety_denial_wins():
    result = AgencyGate().authorize(
        proposal(),
        safety_allowed=False,
        verification_status=FactualStatus.VERIFIED,
    )
    assert result.decision is ActionDecision.DENY


def test_cycle_must_be_authorized_before_action_or_outcome():
    cycle = CognitiveCycle(goal="test")
    assert cycle.status is CycleStatus.CREATED

    try:
        cycle.action = {"type": "external-action"}
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized action mutation was accepted")

    outcome = type(
        "OutcomeLike",
        (),
        {
            "prediction_id": "p1",
            "observed_outcome": "executed",
            "observed": True,
            "source": "test",
            "provenance": (),
        },
    )()

    try:
        cycle.record_outcome(outcome)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized outcome was accepted")


def test_authorized_cycle_can_complete():
    cycle = CognitiveCycle(goal="test")
    cycle.authorize("verified and policy-approved")
    cycle.action = {"type": "controlled-action"}

    outcome = type(
        "OutcomeLike",
        (),
        {
            "prediction_id": "p1",
            "observed_outcome": "executed",
            "observed": True,
            "source": "test",
            "provenance": ("source_A",),
        },
    )()
    cycle.record_outcome(outcome)

    assert cycle.status is CycleStatus.COMPLETED
    assert cycle.safety_decision["allowed"] is True
