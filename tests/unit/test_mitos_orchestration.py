"""Unit coverage for bounded MITOS proposal orchestration."""

import pytest

from anne.mythos.candidate import HypothesisCandidate, TaskMode
from anne.mythos.orchestration import (
    MitosOrchestrationStatus,
    MitosOrchestrator,
)


def candidate(
    ident: str,
    *,
    testability: float = 0.8,
    harm_risk: float = 0.0,
) -> HypothesisCandidate:
    return HypothesisCandidate(
        id=ident,
        goal="goal",
        claim=f"claim {ident}",
        mode="hypothesis",
        probability=0.7,
        discovery_value=0.7,
        novelty=0.5,
        testability=testability,
        harm_risk=harm_risk,
        reversibility=1.0,
        expected_benefit=0.6,
        test_cost=0.2,
        evidence_status="UNVERIFIED",
        score_origin="test",
    )


def test_empty_proposals_are_bounded_without_execution():
    result = MitosOrchestrator().evaluate([])

    assert result.status is MitosOrchestrationStatus.NO_ELIGIBLE_PROPOSAL
    assert result.selected_candidate is None
    assert result.proposals.candidates == ()


def test_proposals_are_bounded_by_budget():
    result = MitosOrchestrator(max_candidates=2).evaluate(
        [candidate("a"), candidate("b"), candidate("c")],
        budget=2,
    )

    assert len(result.proposals.candidates) == 2
    assert [item.id for item in result.proposals.candidates] == ["a", "b"]


def test_eligible_proposal_is_selected_but_not_executed():
    result = MitosOrchestrator().evaluate(
        [candidate("a")],
        task_mode=TaskMode.TECHNICAL,
    )

    assert result.status is MitosOrchestrationStatus.SELECTED
    assert result.selected_candidate is not None
    assert "unexecuted" in result.next_action[0].lower()


def test_harmful_proposal_does_not_pass_gate():
    result = MitosOrchestrator().evaluate(
        [candidate("unsafe", harm_risk=0.2)],
    )

    assert result.status is MitosOrchestrationStatus.NO_ELIGIBLE_PROPOSAL
    assert result.selected_candidate is None


def test_un_testable_proposal_does_not_pass_gate():
    result = MitosOrchestrator().evaluate(
        [candidate("untestable", testability=0.1)],
    )

    assert result.status is MitosOrchestrationStatus.NO_ELIGIBLE_PROPOSAL
    assert result.selected_candidate is None


def test_invalid_budget_is_rejected():
    with pytest.raises(ValueError):
        MitosOrchestrator().evaluate([candidate("a")], budget=0)


def test_serialization_preserves_proposal_batch():
    result = MitosOrchestrator().evaluate([candidate("a"), candidate("b")])
    payload = result.as_dict()

    assert payload["proposals"]["budget"] == 8
    assert len(payload["proposals"]["candidates"]) == 2
