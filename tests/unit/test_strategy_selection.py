"""Unit coverage for deterministic Strategy Selection v1."""

from anne.core.failure_learning import FailureLearningEngine
from anne.core.self_correction import FailureClass
from anne.core.strategy_selection import (
    StrategyCandidate,
    StrategySelectionStatus,
    StrategySelector,
)


def _learning(meta_tag: str = "logical", strategy: str = "old_strategy"):
    return FailureLearningEngine().learn(
        {
            "id": "f1",
            "meta_tag": meta_tag,
            "reason": "test failure",
            "strategy": strategy,
        }
    )


def test_single_safe_candidate_is_selected():
    learning = _learning()
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate(
                strategy_id="rebuild_reasoning",
                failure_class=FailureClass.LOGICAL,
                rationale="rebuild from constraints",
            )
        ],
    )

    assert result.status is StrategySelectionStatus.SELECTED
    assert result.selected is not None
    assert result.selected.strategy_id == "rebuild_reasoning"


def test_attempted_strategy_is_never_selected_again():
    learning = _learning()
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate(
                strategy_id="rebuild_reasoning",
                failure_class=FailureClass.LOGICAL,
                rationale="same path",
            )
        ],
        attempted_strategy="rebuild_reasoning",
    )

    assert result.status is StrategySelectionStatus.NO_VALID_STRATEGY
    assert result.selected is None
    assert result.rejected[0][1] == "same_as_attempted_strategy"


def test_multiple_valid_candidates_are_preserved_without_silent_choice():
    learning = _learning()
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate("a_strategy", FailureClass.LOGICAL, "option a"),
            StrategyCandidate("b_strategy", FailureClass.LOGICAL, "option b"),
        ],
    )

    assert result.status is StrategySelectionStatus.MULTIPLE_VALID
    assert result.selected is None
    assert [item.strategy_id for item in result.candidates] == [
        "a_strategy",
        "b_strategy",
    ]


def test_exhausted_learning_abstains():
    learning = FailureLearningEngine().learn(
        {"id": "f1", "meta_tag": "logical", "reason": "failure"},
        retry_index=2,
        max_retries=2,
    )
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate("safe", FailureClass.LOGICAL, "safe alternative"),
        ],
    )

    assert result.status is StrategySelectionStatus.ABSTAIN
    assert result.selected is None


def test_unsafe_and_mismatched_candidates_are_rejected():
    learning = _learning()
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate("unsafe", FailureClass.LOGICAL, "unsafe", safe=False),
            StrategyCandidate("wrong", FailureClass.FACTUAL, "wrong class"),
        ],
    )

    assert result.status is StrategySelectionStatus.NO_VALID_STRATEGY
    assert {reason for _, reason in result.rejected} == {
        "unsafe_candidate",
        "failure_class_mismatch",
    }


def test_selection_order_is_deterministic():
    learning = _learning()
    candidates = [
        StrategyCandidate("z_strategy", FailureClass.LOGICAL, "z"),
        StrategyCandidate("a_strategy", FailureClass.LOGICAL, "a"),
    ]

    first = StrategySelector().select(learning, candidates)
    second = StrategySelector().select(learning, reversed(candidates))

    assert [item.strategy_id for item in first.candidates] == [
        "a_strategy",
        "z_strategy",
    ]
    assert first.as_dict() == second.as_dict()


def test_execution_risk_failure_cannot_select_a_strategy():
    learning = _learning(meta_tag="execution", strategy="unsafe_path")
    result = StrategySelector().select(
        learning,
        [
            StrategyCandidate(
                "safe_alternative",
                FailureClass.EXECUTION_RISK,
                "still requires authority",
            )
        ],
    )

    assert result.status is StrategySelectionStatus.ABSTAIN
