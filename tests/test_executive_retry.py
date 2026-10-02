from anne.core.cognitive_orchestrator import CognitiveOrchestrator
from anne.core.failure_recovery import FailureRecoveryController
from anne.core.pipeline import AnnePipeline
from anne.core.decision_loop import DecisionLoop
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.candidate import HypothesisCandidate, SelectionResult, TaskMode
from anne.mythos.engine import ExplorationMode


def _candidate(goal: str, claim: str, probability: float = 0.7) -> HypothesisCandidate:
    return HypothesisCandidate(
        id=goal.replace(" ", "_").lower(),
        goal=goal,
        claim=claim,
        probability=probability,
        mode=ExplorationMode.HYPOTHESIS,
        discovery_value=0.5,
        novelty=0.5,
        testability=0.5,
        harm_risk=0.0,
        reversibility=1.0,
        expected_benefit=0.5,
        test_cost=0.1,
    )


def test_retry_controller_stops_repeated_frames() -> None:
    decision = FailureRecoveryController.authorize_retry(
        attempt=1,
        max_retries=2,
        seen_questions={"same frame"},
        question="Same   Frame",
    )
    assert decision.allowed is False
    assert decision.reason == "oscillation_detected"


def test_orchestrator_rejects_negative_retry_budget(tmp_path) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    pipeline = AnnePipeline(memory=memory)
    try:
        CognitiveOrchestrator(pipeline, max_retries=-1)
    except ValueError as exc:
        assert "max_retries" in str(exc)
    else:
        raise AssertionError("negative retry budget must be rejected")


def test_orchestrator_success_exposes_lineage(tmp_path) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    result = DecisionLoop(memory=memory).run_cognitive("2 + 2", seed=1)
    assert result.status in {"EXECUTED", "BOUNDED", "ABORTED"}
    assert result.lineage
    assert result.retry_count >= 0


def test_candidate_contract_matches_runtime() -> None:
    candidate = _candidate("first", "first claim")
    assert candidate.goal == "first"
    assert candidate.claim == "first claim"
    assert candidate.probability == 0.7


def test_selector_result_contract_matches_candidate() -> None:
    candidate = _candidate("first", "first claim")
    result = SelectionResult(
        candidate=candidate,
        accepted=True,
        score=0.8,
        reason="accepted",
        considered=1,
    )
    assert result.candidate is candidate
    assert result.accepted is True
    assert result.considered == 1


def test_task_mode_contract_remains_available() -> None:
    assert TaskMode.TECHNICAL.value == "technical"

def test_failure_trace_persists_structured_learning_signal(tmp_path) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    trace_id = memory.save_failure_trace(
        cycle_id="cycle-learning",
        stage="YAP",
        raw_input="test question",
        reason="insufficient evidence",
        meta_tag="executive_retry",
        learning_failure_class="evidence_gap",
        learning_strategy="seek_missing_evidence_or_abstain",
        learning_lesson="Previous attempt failed; do not treat it as validated knowledge.",
        learning_confidence=0.5,
        learning_safe_to_reuse=False,
    )

    row = memory.get_recent_failures(limit=1)[0]
    assert row[0] == trace_id
    assert row[7] == "evidence_gap"
    assert row[8] == "seek_missing_evidence_or_abstain"
    assert row[9].startswith("Previous attempt failed")
    assert row[10] == 0.5
    assert row[11] == 0


def test_orchestrator_persists_learning_signal_for_selection_failure(tmp_path) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    pipeline = AnnePipeline(memory=memory)

    class RejectingSelector:
        def select(self, candidates, *, task_mode):
            del candidates, task_mode
            return SelectionResult(
                candidate=None,
                accepted=False,
                score=0.0,
                reason="insufficient evidence",
                considered=0,
            )

    result = CognitiveOrchestrator(
        pipeline,
        selector=RejectingSelector(),
        max_retries=0,
    ).run("test question", seed=1)

    assert result.stop_reason == "selection_rejected"
    row = memory.get_recent_failures(limit=1)[0]
    assert row[7] == "evidence_gap"
    assert row[8] == "seek_missing_evidence_or_abstain"
    assert row[11] == 0

def test_orchestrator_stops_at_retry_budget_on_repeated_yap_failure(tmp_path, monkeypatch) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    pipeline = AnnePipeline(memory=memory)

    def always_fail_anla(state, hypothesis, *, claim_verifier=None):
        del hypothesis, claim_verifier
        state.logic_valid = False
        state.ethic_score = None
        state.context_map["anla_score"] = 0.1
        return state

    monkeypatch.setattr(pipeline, "anla", always_fail_anla)

    result = CognitiveOrchestrator(
        pipeline,
        max_retries=2,
    ).run("Evaluate a bounded technical option", seed=7)

    assert result.status == "BOUNDED"
    assert result.retry_count == 2
    assert result.stop_reason == "retry_budget_exhausted"
    assert len(result.lineage) == 3


def test_orchestrator_zero_retry_budget_never_retries(tmp_path, monkeypatch) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    pipeline = AnnePipeline(memory=memory)

    def always_fail_anla(state, hypothesis, *, claim_verifier=None):
        del hypothesis, claim_verifier
        state.logic_valid = False
        state.ethic_score = None
        state.context_map["anla_score"] = 0.1
        return state

    monkeypatch.setattr(pipeline, "anla", always_fail_anla)

    result = CognitiveOrchestrator(
        pipeline,
        max_retries=0,
    ).run("Evaluate a bounded technical option", seed=7)

    assert result.status == "BOUNDED"
    assert result.retry_count == 0
    assert result.stop_reason == "retry_budget_exhausted"
    assert len(result.lineage) == 1
