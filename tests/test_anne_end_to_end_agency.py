"""End-to-end contract test for the real ANNE cognitive-to-agency path."""

from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from anne.core.cognitive_cycle import CognitiveCycle, Observation, Outcome
from anne.core.cognitive_runtime import CognitiveWorkspace, HierarchicalPlanner, Metacognition
from anne.core.verification import FactualStatus, ReferenceClaim, ReferenceVerifier, verify_claim
from anne.mythos.engine import MitosEngine


def test_anne_real_stack_verified_candidate_can_execute() -> None:
    goal = "select a bounded, testable research pathway"

    # MITOS is used as the discovery layer; its candidate is not treated as fact.
    candidate = MitosEngine(seed=7).generate(goal, batch_size=1)[0]
    assert candidate.evidence_status == "SIMULATION"

    workspace = CognitiveWorkspace(task=goal, uncertainty=0.10)
    planner = HierarchicalPlanner(max_goals=6)
    goals = planner.create_plan(workspace)
    assert goals[0].status == "active"
    assert planner.next_goal(workspace) is not None

    cycle = CognitiveCycle(goal=goal)
    cycle.add_observation(
        Observation(
            content=candidate.claim,
            source="MITOS",
            observed_at="test",
            provenance=(candidate.id,),
        )
    )
    workspace.observations.append(candidate.claim)
    workspace.record_tool_result("bounded-evidence", "candidate inspected", ok=True)

    # Independent verification is required before agency.
    verifier = ReferenceVerifier(
        [ReferenceClaim(candidate.claim, "independent_test_source", supported=True)]
    )
    verification = verify_claim(candidate.claim, verifier)
    assert verification.status is FactualStatus.VERIFIED

    review = Metacognition().review(workspace, response="A bounded candidate was independently verified.")
    assert review.needs_verification is False

    proposal = ActionProposal(
        action="record_verified_candidate",
        target="test-ledger",
        reversible=True,
        risk=0.10,
        provenance=verification.sources + (candidate.id,),
    )
    authorization = AgencyGate().authorize(
        proposal,
        safety_allowed=True,
        verification_status=verification.status,
        needs_verification=review.needs_verification,
    )
    assert authorization.decision is ActionDecision.ALLOW

    cycle.authorize(authorization.reason)
    cycle.action = {"type": proposal.action, "target": proposal.target}
    cycle.record_outcome(
        Outcome(
            prediction_id="none",
            observed_outcome="recorded",
            observed=True,
            source="test-ledger",
            provenance=proposal.provenance,
        )
    )

    assert cycle.status.value == "COMPLETED"
    assert cycle.safety_decision["allowed"] is True
    assert cycle.provenance


def test_anne_real_stack_blocks_unverified_candidate() -> None:
    goal = "evaluate an unverified discovery"
    candidate = MitosEngine(seed=11).generate(goal, batch_size=1)[0]
    workspace = CognitiveWorkspace(task=goal, uncertainty=0.10)
    workspace.observations.append(candidate.claim)
    workspace.record_tool_result("bounded-evidence", "candidate inspected", ok=True)

    verification = verify_claim(candidate.claim)
    review = Metacognition().review(workspace, response="Candidate requires independent evidence.")
    assert verification.status is FactualStatus.UNVERIFIED

    proposal = ActionProposal(
        action="external-action",
        target="test-ledger",
        risk=0.10,
        provenance=(candidate.id,),
    )
    authorization = AgencyGate().authorize(
        proposal,
        safety_allowed=True,
        verification_status=verification.status,
        needs_verification=review.needs_verification,
    )
    assert authorization.decision is ActionDecision.DENY

    cycle = CognitiveCycle(goal=goal)
    cycle.block(authorization.reason)
    assert cycle.status.value == "BLOCKED"
    assert cycle.safety_decision["allowed"] is False
