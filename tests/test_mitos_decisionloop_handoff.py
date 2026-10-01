"""Held-out-style regression for the MITOS -> DecisionLoop research handoff."""

from __future__ import annotations

from anne.core.decision_loop import DecisionLoop
from anne.mythos.experience import ExperienceRecord, ExperienceStatus


def _failed_mitos(hypothesis_id: str, context: dict[str, str]) -> ExperienceRecord:
    return ExperienceRecord(
        hypothesis_id=hypothesis_id,
        goal="bounded safety test",
        claim="synthetic claim",
        status=ExperienceStatus.FAILED,
        context=context,
    )


def _outcomes(context: dict[str, str]) -> tuple[ExperienceRecord, ...]:
    return (
        _failed_mitos("m1", context),
        _failed_mitos("m2", context),
    )


def test_repeated_mitos_failures_trigger_research_handoff(
    tmp_path,
) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))

    result = loop.run(
        "Bu iddianın kaynağı nedir?",
        learning_context={"key": "mitos", "conditions": {"mode": "research"}},
        strategy="bounded_test",
        mitos_outcomes=_outcomes({"mode": "research"}),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert result.research_state is not None
    assert result.research_state.adaptive_learning is not None
    assert result.research_state.adaptive_learning.strategy.action == "CHANGE"
    assert (
        result.research_state.adaptive_learning.strategy.strategy
        == "seek_fresh_independent_evidence"
    )
    assert result.research_state.decision.action == "RESEARCH"

    assert result.action == "RESEARCH"
    assert result.status == "BOUNDED"


def test_cross_context_mitos_failures_do_not_trigger_decisionloop_strategy_change(
    tmp_path,
) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))

    result = loop.run(
        "Bu işlem güvenli mi?",
        learning_context={"key": "mitos", "conditions": {"mode": "research"}},
        strategy="bounded_test",
        mitos_outcomes=_outcomes({"mode": "production"}),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert result.research_state is not None
    assert result.research_state.adaptive_learning is not None
    assert result.research_state.adaptive_learning.strategy.action == "KEEP"
    assert result.research_state.adaptive_learning.strategy.strategy == "bounded_test"
    assert result.action == "HALT"
    assert result.output.get("authority_check_required") is True


def test_authority_failure_does_not_get_replaced_by_mitos_learning(
    tmp_path,
) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))

    result = loop.run(
        "Bu işlem güvenli mi?",
        learning_context={"key": "mitos", "conditions": {"mode": "research"}},
        strategy="bounded_test",
        mitos_outcomes=_outcomes({"mode": "research"}),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert result.research_state is not None
    assert result.research_state.adaptive_learning is not None
    assert result.research_state.adaptive_learning.strategy.action == "ABSTAIN"
    assert result.action == "HALT"
    assert result.output.get("authority_check_required") is True
