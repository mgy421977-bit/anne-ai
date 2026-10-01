"""Runtime boundary regressions for MITOS learning and guarded handoff."""

from __future__ import annotations

from anne.core.decision_loop import DecisionLoop
from anne.core.trace import CycleTrace
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop
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


def _evidence_gap_trace(context: dict[str, str]) -> CycleTrace:
    return CycleTrace(
        cycle_id="completed-cycle",
        status="BOUNDED",
        stop_reason="evidence_gap",
        intent={"requires_evidence": True},
        learning={
            "context": {
                "key": "mitos",
                "conditions": context,
            }
        },
    )


def test_repeated_mitos_failures_trigger_research_handoff() -> None:
    state = ResearchCognitiveLoop().initialize(
        "Bu iddianın kaynağı nedir?",
        completed_trace=_evidence_gap_trace({"mode": "research"}),
        strategy="bounded_test",
        mitos_outcomes=_outcomes({"mode": "research"}),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert state.adaptive_learning is not None
    assert state.adaptive_learning.strategy.action == "CHANGE"
    assert (
        state.adaptive_learning.strategy.strategy
        == "seek_fresh_independent_evidence"
    )
    assert state.decision.action == "REVIEW"
    assert state.decision.research_allowed is False


def test_cross_context_mitos_failures_do_not_change_research_strategy() -> None:
    state = ResearchCognitiveLoop().initialize(
        "Bu iddianın kaynağı nedir?",
        completed_trace=_evidence_gap_trace({"mode": "research"}),
        strategy="bounded_test",
        mitos_outcomes=_outcomes({"mode": "production"}),
        mitos_failure_classes={
            "m1": "evidence_gap",
            "m2": "evidence_gap",
        },
    )

    assert state.adaptive_learning is not None
    assert state.adaptive_learning.strategy.action == "KEEP"
    assert state.adaptive_learning.strategy.strategy == "bounded_test"


def test_decisionloop_runtime_wires_mitos_strategy_change_without_authority() -> None:
    loop = DecisionLoop(memory_db_path=":memory:")

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
    assert result.research_state.adaptive_learning.strategy.action == "CHANGE"
    assert (
        result.research_state.adaptive_learning.strategy.strategy
        == "seek_fresh_independent_evidence"
    )
    assert result.research_state.decision.action == "REVIEW"
    assert result.research_state.decision.research_allowed is False

    # The runtime exposes the bounded handoff but the enclosing decision
    # remains fail-closed and cannot become execution authority.
    assert result.action == "HALT"


def test_decisionloop_authority_boundary_remains_halt() -> None:
    loop = DecisionLoop(memory_db_path=":memory:")

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

    assert result.action == "HALT"
    assert result.output.get("authority_check_required") is True
