"""Unit coverage for the closed Decision Synthesis → METACOG → SFT loop."""

from anne.core.decision_synthesis import (
    EvidenceLink,
    EvidenceRelation,
    SynthesisHypothesis,
)
from anne.core.feedback_loop import DecisionFeedbackLoop
from anne.core.metacognition import MetaStatus


def test_supported_synthesis_reaches_ready_without_failure():
    hypothesis = SynthesisHypothesis(id="h1", claim="bounded claim")
    # Build the synthesis through the canonical DecisionSynthesizer.
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [hypothesis],
        evidence=[
            EvidenceLink(
                evidence_id="e1",
                hypothesis_id="h1",
                relation=EvidenceRelation.SUPPORTS,
            )
        ],
    )
    cycle = DecisionFeedbackLoop().evaluate(decision)

    assert cycle.review.status is MetaStatus.READY
    assert cycle.retry_allowed is False
    assert cycle.failure_learning == ()


def test_first_failure_creates_bounded_recovery_signal():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")],
        evidence=[
            EvidenceLink(
                evidence_id="e1",
                hypothesis_id="h1",
                relation=EvidenceRelation.SUPPORTS,
            )
        ],
        failure_trace=[
            {
                "id": "f1",
                "meta_tag": "evidence_gap",
                "reason": "missing source",
                "strategy": "initial_search",
            }
        ],
    )
    cycle = DecisionFeedbackLoop().evaluate(decision)

    assert cycle.review.status is MetaStatus.REVIEW
    assert len(cycle.failure_learning) == 1
    assert cycle.retry_allowed is True
    assert cycle.failure_learning[0].lesson.validated is False


def test_repeated_failure_with_same_strategy_blocks_unchanged_retry():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")],
        evidence=[
            EvidenceLink(
                evidence_id="e1",
                hypothesis_id="h1",
                relation=EvidenceRelation.SUPPORTS,
            )
        ],
        failure_trace=[
            {
                "id": "f2",
                "meta_tag": "logical",
                "reason": "constraint conflict",
                "strategy": "rebuild_reasoning_from_constraints",
            }
        ],
    )
    cycle = DecisionFeedbackLoop().evaluate(
        decision,
        prior_failures=[
            {
                "id": "f2",
                "reason": "constraint conflict",
                "strategy": "rebuild_reasoning_from_constraints",
            }
        ],
        attempted_strategy="rebuild_reasoning_from_constraints",
        retry_index=1,
    )

    assert cycle.strategy_change_required is True
    assert cycle.retry_allowed is False


def test_new_strategy_keeps_retry_bounded_and_requires_verification():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")],
        evidence=[
            EvidenceLink(
                evidence_id="e1",
                hypothesis_id="h1",
                relation=EvidenceRelation.SUPPORTS,
            )
        ],
        failure_trace=[
            {
                "id": "f3",
                "meta_tag": "factual",
                "reason": "source mismatch",
                "strategy": "initial_source",
            }
        ],
    )
    cycle = DecisionFeedbackLoop().evaluate(
        decision,
        prior_failures=[
            {
                "id": "f3",
                "reason": "source mismatch",
                "strategy": "initial_source",
            }
        ],
        attempted_strategy="independent_source_check",
        retry_index=1,
    )

    assert cycle.retry_allowed is True
    assert cycle.strategy_change_required is False
    assert any("re-verify" in action.lower() for action in cycle.next_action)


def test_exhausted_feedback_cannot_retry():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")],
        evidence=[
            EvidenceLink(
                evidence_id="e1",
                hypothesis_id="h1",
                relation=EvidenceRelation.SUPPORTS,
            )
        ],
        failure_trace=[
            {
                "id": "f4",
                "meta_tag": "uncertainty",
                "reason": "ambiguity remains",
            }
        ],
    )
    cycle = DecisionFeedbackLoop().evaluate(
        decision,
        retry_index=2,
        max_retries=2,
    )

    assert cycle.exhausted is True
    assert cycle.retry_allowed is False


def test_abstention_status_blocks_retry():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")]
    )
    cycle = DecisionFeedbackLoop().evaluate(decision)

    assert cycle.review.status is MetaStatus.ABSTAIN
    assert cycle.retry_allowed is False


def test_cycle_serialization_preserves_non_authoritative_learning():
    from anne.core.decision_synthesis import DecisionSynthesizer

    decision = DecisionSynthesizer().synthesize(
        [SynthesisHypothesis(id="h1", claim="claim")],
        failure_trace=[
            {
                "id": "f5",
                "meta_tag": "semantic",
                "reason": "interpretation mismatch",
            }
        ],
    )
    payload = DecisionFeedbackLoop().evaluate(decision).as_dict()

    assert payload["failure_learning"][0]["lesson"]["validated"] is False
    assert payload["failure_learning"][0]["lesson"]["safe_to_reuse"] is False
    assert payload["retry_allowed"] is False
