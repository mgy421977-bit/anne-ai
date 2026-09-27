"""Unit coverage for bounded failure-learning feedback."""

from anne.core.failure_learning import (
    FailureLearningEngine,
    FailureLearningStatus,
)
from anne.core.self_correction import FailureClass


def test_first_failure_is_recorded_without_becoming_knowledge():
    result = FailureLearningEngine().learn(
        {
            "id": "f-1",
            "meta_tag": "evidence_gap",
            "reason": "missing source evidence",
            "original": "Verify the claim",
        }
    )

    assert result.status is FailureLearningStatus.RECORDED
    assert result.lesson.failure_class is FailureClass.EVIDENCE_GAP
    assert result.lesson.validated is False
    assert result.lesson.safe_to_reuse is False
    assert result.lesson.recommended_strategy == "seek_missing_evidence_or_abstain"


def test_same_failure_and_same_strategy_requires_strategy_change():
    result = FailureLearningEngine().learn(
        {
            "id": "f-2",
            "meta_tag": "logical",
            "reason": "constraint conflict",
            "original": "Solve the constrained problem",
        },
        prior_failures=[
            {
                "id": "f-2",
                "reason": "constraint conflict",
                "strategy": "rebuild_reasoning_from_constraints",
            }
        ],
        attempted_strategy="rebuild_reasoning_from_constraints",
        retry_index=1,
    )

    assert result.status is FailureLearningStatus.STRATEGY_CHANGE_REQUIRED
    assert result.lesson.repeated is True
    assert result.lesson.strategy_change_required is True
    assert "Do not repeat" in result.next_action[0]


def test_same_failure_with_different_strategy_can_continue_bounded():
    result = FailureLearningEngine().learn(
        {
            "id": "f-3",
            "meta_tag": "factual",
            "reason": "source mismatch",
            "original": "Check the fact",
        },
        prior_failures=[
            {
                "id": "f-3",
                "reason": "source mismatch",
                "strategy": "request_or_recheck_evidence",
            }
        ],
        attempted_strategy="independent_source_check",
        retry_index=1,
    )

    assert result.status is FailureLearningStatus.RECORDED
    assert result.lesson.repeated is True
    assert result.lesson.strategy_change_required is False


def test_retry_budget_exhaustion_abstains():
    result = FailureLearningEngine().learn(
        {
            "id": "f-4",
            "meta_tag": "uncertainty",
            "reason": "evidence remains ambiguous",
            "original": "Choose a conclusion",
        },
        retry_index=2,
        max_retries=2,
    )

    assert result.status is FailureLearningStatus.EXHAUSTED
    assert result.reframe_plan.exhausted is True
    assert "Do not retry" in result.next_action[0]


def test_ethical_failure_requires_abstention():
    result = FailureLearningEngine().learn(
        {
            "id": "f-5",
            "meta_tag": "ethical",
            "reason": "unsafe path requested",
            "original": "Execute the requested action",
        }
    )

    assert result.status is FailureLearningStatus.ABSTAIN
    assert result.lesson.failure_class is FailureClass.ETHICAL
    assert result.lesson.recommended_strategy == "halt_and_require_safe_alternative"


def test_missing_strategy_on_repeated_failure_is_conservative():
    result = FailureLearningEngine().learn(
        {
            "id": "f-6",
            "meta_tag": "semantic",
            "reason": "claim interpretation mismatch",
        },
        prior_failures=[
            {
                "id": "f-6",
                "reason": "claim interpretation mismatch",
                "strategy": "clarify_claim_and_revalidate",
            }
        ],
        retry_index=1,
    )

    assert result.status is FailureLearningStatus.STRATEGY_CHANGE_REQUIRED
    assert result.lesson.strategy_change_required is True


def test_as_dict_exposes_non_authoritative_feedback():
    result = FailureLearningEngine().learn(
        {
            "id": "f-7",
            "meta_tag": "procedural",
            "reason": "step order was invalid",
            "original": "Run the procedure",
        }
    )

    payload = result.as_dict()

    assert payload["lesson"]["validated"] is False
    assert payload["lesson"]["safe_to_reuse"] is False
    assert payload["reframe_plan"]["failure_class"] == "procedural"
