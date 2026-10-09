from anne.core.failure_recovery import (
    FailureKind,
    FailureRecoveryController,
    FailureSignal,
)


def test_failure_is_classified_and_reframed_without_authority() -> None:
    failure = FailureSignal(
        kind=FailureKind.SEMANTIC,
        reason="Semantic Validation Layer blocked output",
        stage="YAP",
        cycle_id="cycle-1",
        depth=1,
    )
    plan = FailureRecoveryController.plan(failure, "BESS nedir?", attempt=2)

    assert plan.strategy == "clarify_claim"
    assert plan.question.startswith("Clarify the claim:")
    assert plan.parent_cycle_id == "cycle-1"
    assert plan.depth == 2
    assert plan.attempt == 2


def test_retry_budget_is_hard_boundary() -> None:
    decision = FailureRecoveryController.authorize_retry(
        attempt=3,
        max_retries=3,
        seen_questions=set(),
        question="new frame",
    )

    assert decision.allowed is False
    assert decision.reason == "retry_budget_exhausted"


def test_retry_rejects_repeated_frame_as_oscillation() -> None:
    decision = FailureRecoveryController.authorize_retry(
        attempt=1,
        max_retries=3,
        seen_questions={"same frame"},
        question="same frame",
    )

    assert decision.allowed is False
    assert decision.reason == "oscillation_detected"


def test_retry_authorization_is_bounded_and_non_authoritative() -> None:
    decision = FailureRecoveryController.authorize_retry(
        attempt=1,
        max_retries=3,
        seen_questions={"original"},
        question="new frame",
    )

    assert decision.allowed is True
    assert decision.next_attempt == 2
    assert decision.reason == "retry_authorized"

def test_explicit_selected_strategy_can_shape_bounded_reframe() -> None:
    failure = FailureSignal(
        kind=FailureKind.EVIDENCE_GAP,
        reason="insufficient evidence",
        stage="YAP",
        cycle_id="cycle-selected",
        depth=0,
    )
    plan = FailureRecoveryController.plan(
        failure,
        "Claim X",
        attempt=1,
        preferred_strategy="recheck_independent_evidence",
    )

    assert plan.strategy == "recheck_independent_evidence"
    assert plan.question.startswith("Recheck the claim against independent evidence:")


def test_unknown_selected_strategy_falls_back_to_failure_kind() -> None:
    failure = FailureSignal(
        kind=FailureKind.EVIDENCE_GAP,
        reason="missing evidence",
        stage="YAP",
        cycle_id="cycle-fallback",
        depth=0,
    )
    plan = FailureRecoveryController.plan(
        failure,
        "Claim Y",
        attempt=1,
        preferred_strategy="unknown",
    )

    assert plan.strategy == "seek_missing_evidence"

from anne.core.failure_recovery import FailureKind, FailureRecoveryController, FailureSignal


def test_resource_failure_routes_to_computation_escalation() -> None:
    assert FailureRecoveryController.classify("compute budget exhausted", "YAP") is FailureKind.RESOURCE_INSUFFICIENCY
    plan = FailureRecoveryController.plan(
        FailureSignal(FailureKind.RESOURCE_INSUFFICIENCY, "compute timeout", "YAP", "c1", 0),
        "solve the problem",
        attempt=1,
    )
    assert plan.strategy == "escalate_computation"
    assert plan.question.startswith("Escalate computation for:")


def test_wrong_hypothesis_does_not_route_to_more_compute() -> None:
    kind = FailureRecoveryController.classify("wrong hypothesis; new hypothesis needed", "SELECT")
    assert kind is FailureKind.HYPOTHESIS_FAILURE
    plan = FailureRecoveryController.plan(
        FailureSignal(kind, "wrong hypothesis", "SELECT", "c2", 0),
        "solve the problem",
        attempt=1,
    )
    assert plan.strategy == "generate_new_hypothesis"


def test_relation_and_verification_failures_have_distinct_recovery() -> None:
    assert FailureRecoveryController.classify("relation gap", "EPISTEMIC") is FailureKind.RELATION_GAP
    assert FailureRecoveryController.classify("cannot verify result", "VERIFY") is FailureKind.VERIFICATION_GAP
