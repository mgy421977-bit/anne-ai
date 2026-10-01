from dataclasses import replace
from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.learning.critic_loop import LoopDecision
from anne.language.corroboration import LanguageCorroborationResult
from anne.language.policy import LanguageCheckDecision
from anne.language.verification import LanguageVerificationResult, LanguageVerificationStatus
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


class _FakeOrchestrator:
    def __init__(self, result: OrchestrationResult) -> None:
        self.result = result

    def run(self, *args, **kwargs) -> OrchestrationResult:
        return self.result


class _ProceedCritic:
    def decide(self, *args, **kwargs) -> LoopDecision:
        return LoopDecision(
            action="PROCEED",
            reason="test bounded loop permits continuation",
            research_allowed=True,
        )


def _decision_loop_for_state(
    *,
    verification_status: str,
    verification_sources: tuple[str, ...] = (),
    requires_evidence: bool = True,
    include_intent: bool = True,
    lineage_id: str = "or_runtime_test",
    memory_db_path: str | None = None,
) -> DecisionLoop:
    fail_fast = FailFastResult(True, "ok")
    state = SimpleNamespace(
        output={"verdict": "ONAYLA", "action": "PROCEED", "reason": "test decision"},
        action="PROCEED",
        context_map={
            "verification_status": verification_status,
            "verification_sources": verification_sources,
            "requires_evidence": requires_evidence,
            **({"intent": "answer"} if include_intent else {}),
        },
        ethic_score=None,
    )
    orchestration = OrchestrationResult(
        status="EXECUTED",
        fail_fast=fail_fast,
        state=state,
        selection=None,
        stage_trace=("FAIL_FAST", "DUY", "SELECT", "ANLA", "YAP"),
        reason="test decision",
        retry_count=0,
        lineage=(lineage_id,),
        stop_reason="validated",
    )
    loop = DecisionLoop.__new__(DecisionLoop)
    if memory_db_path is not None:
        loop.memory = FractalMemory(memory_db_path)
    loop.orchestrator = _FakeOrchestrator(orchestration)
    loop.research_loop = ResearchCognitiveLoop(critic_loop=_ProceedCritic(), memory=getattr(loop, "memory", None))
    loop._experience_history = ()
    loop._experience_history_limit = 64
    return loop


def test_runtime_routes_verified_trace_with_missing_intent_to_review() -> None:
    loop = _decision_loop_for_state(
        verification_status="VERIFIED",
        verification_sources=("source-a",),
        include_intent=False,
    )

    result = loop.run("Question")

    assert result.status == "BOUNDED"
    assert result.verdict == "REVIEW"
    assert result.action == "REVIEW"
    assert result.research_state is not None
    assert result.research_state.adaptive_learning is not None
    assert (
        result.research_state.adaptive_learning.metacognition.requires_review is True
    )
    assert result.trace is not None
    assert result.trace.learning["metacognition"]["requires_review"] is True


def test_runtime_routes_unverified_trace_to_bounded_research() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")

    assert result.status == "BOUNDED"
    assert result.verdict == "RESEARCH"
    assert result.action == "RESEARCH"
    assert result.research_state is not None
    assert result.research_state.decision.action == "RESEARCH"
    assert result.output["research_questions"]
    assert result.trace is not None
    assert result.trace.learning["metacognition"]["research_required"] is True


def test_runtime_metacognition_never_grants_execution_authority() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")

    assert result.output["action"] == "RESEARCH"
    assert result.output["metacognitive_next_step"] == "RESEARCH"
    assert result.output["original_output"]["action"] == "PROCEED"


def test_runtime_serializes_bounded_research_guidance() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    result = loop.run("Question")
    payload = result.as_dict()

    assert payload["research"]["action"] == "RESEARCH"
    assert payload["research"]["research_allowed"] is True
    assert payload["research"]["questions"]

from anne.core.verification import FactualStatus
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.evidence import EvidenceItem, EvidenceLedgerEntry
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.reevaluation_loop import ReEvaluationLoop
from anne.memory.fractal_memory import FractalMemory


class _FakeReevaluationResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        claim = "The answer is supported."
        return [
            EvidenceItem(
                source="source-a",
                claim=claim,
                kind="web",
                provenance="https://alpha.example/a",
                confidence=0.9,
                passage=claim,
            ),
            EvidenceItem(
                source="source-b",
                claim=claim,
                kind="web",
                provenance="https://beta.example/b",
                confidence=0.9,
                passage=f"Independent source confirms: {claim}",
            ),
        ]


def test_runtime_research_reassessment_learning_second_cycle() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")

    first = loop.run("The answer is supported.")

    assert first.status == "BOUNDED"
    assert first.action == "RESEARCH"
    assert first.research_state is not None
    assert first.trace is not None

    state = first.research_state
    hypothesis = state.hypotheses[0]
    old_id = state.evidence_ledger.record(
        EvidenceLedgerEntry(
            claim=hypothesis.claim,
            source="old",
            provenance="https://old.example/a",
            confidence=0.9,
            passage=hypothesis.claim,
        )
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(old_id, hypothesis.id, "supports")
    )
    state.evidence_ledger.graph.add_node(
        ProvenanceNode("A1", "answer", hypothesis.claim)
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(hypothesis.id, "A1", "derived_from")
    )

    refreshed = loop.research_loop.reassess_after_invalidation(
        state,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
        loop=ReEvaluationLoop(
            research_executor=DerivedResearchExecutor(
                researcher=_FakeReevaluationResearcher()
            )
        ),
    )

    assert refreshed.re_evaluation is not None
    assert refreshed.re_evaluation.verification is not None
    assert refreshed.re_evaluation.verification.status is FactualStatus.VERIFIED
    assert refreshed.re_evaluation.rebuild is not None
    assert refreshed.re_evaluation.rebuild.action == "REACTIVATED"

    fresh_ids = {
        evidence_id
        for evidence_id, entry in refreshed.evidence_ledger._entries.items()
        if entry.provenance in {
            "https://alpha.example/a",
            "https://beta.example/b",
        }
    }
    assert len(fresh_ids) == 2
    assert old_id not in fresh_ids
    assert all(
        refreshed.evidence_ledger.graph.get(evidence_id).status.value == "active"
        for evidence_id in fresh_ids
    )

    replacement_id = refreshed.re_evaluation.rebuild.replacement_node
    replacement = refreshed.evidence_ledger.graph.get(replacement_id)
    assert replacement.status.value == "active"
    replacement_edges = [
        edge
        for edge in refreshed.evidence_ledger.graph._edges
        if edge.target_id == replacement_id
    ]
    assert {edge.source_id for edge in replacement_edges} == fresh_ids

    assert refreshed.adaptive_learning is not None
    assert refreshed.adaptive_learning.experience is not None
    experience = refreshed.adaptive_learning.experience
    assert experience.outcome == "SUCCESS"
    assert experience.factual_status == "VERIFIED"
    assert experience.source_cycle_id.startswith("reeval:")
    assert first.research_state.adaptive_learning is not None
    first_experience = first.research_state.adaptive_learning.experience
    assert experience.parent_cycle_id == first_experience.source_cycle_id
    assert experience.lineage == (*first_experience.lineage, experience.source_cycle_id)

    assert refreshed.evidence_ledger.graph.get(old_id).status.value == "invalidated"
    assert refreshed.evidence_ledger.graph.get("A1").status.value == "stale"
    assert refreshed.synthesis.reason
    assert any(
        node.kind == "decision_synthesis"
        and node.content == refreshed.synthesis.reason
        for node in refreshed.evidence_ledger.graph._nodes.values()
    )
    assert refreshed.decision.action in {"PROCEED", "RESEARCH", "REVIEW"}


def test_runtime_hands_off_experience_only_with_exact_explicit_context() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")
    context = {
        "key": "web_research",
        "conditions": {"freshness": "current", "source_count": 2},
    }

    # Force the runtime observation itself to be a bounded failure so that
    # repeated same-context observations can exercise strategy adaptation.
    loop.orchestrator.result = replace(loop.orchestrator.result, status="BOUNDED", stop_reason="evidence_gap")

    first = loop.run(
        "Question",
        learning_context=context,
        strategy="research",
    )
    second = loop.run(
        "Question",
        learning_context=context,
        strategy="research",
    )

    assert first.research_state is not None
    assert first.research_state.adaptive_learning is not None
    assert second.research_state is not None
    assert second.research_state.adaptive_learning is not None
    assert second.research_state.adaptive_learning.strategy.action == "CHANGE"
    assert (
        second.research_state.adaptive_learning.strategy.strategy
        == "seek_fresh_independent_evidence"
    )
    assert second.research_state.adaptive_learning.experience.safe_to_reuse is False


def test_runtime_does_not_cross_contaminate_experience_between_contexts() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")
    loop.orchestrator.result = replace(loop.orchestrator.result, status="BOUNDED", stop_reason="evidence_gap")

    loop.run(
        "Question A",
        learning_context={
            "key": "web_research",
            "conditions": {"freshness": "current"},
        },
        strategy="research",
    )
    isolated = loop.run(
        "Question B",
        learning_context={
            "key": "local_research",
            "conditions": {"freshness": "current"},
        },
        strategy="research",
    )

    assert isolated.research_state is not None
    assert isolated.research_state.adaptive_learning is not None
    assert isolated.research_state.adaptive_learning.strategy.action == "KEEP"
    assert (
        isolated.research_state.adaptive_learning.strategy.strategy
        == "research"
    )


def test_runtime_persists_exact_context_experience_across_restart(tmp_path) -> None:
    db_path = str(tmp_path / "anne.db")
    context = {
        "key": "web_research",
        "conditions": {"freshness": "current", "source_count": 2},
    }

    first_loop = _decision_loop_for_state(
        verification_status="UNVERIFIED",
        lineage_id="or_runtime_persist_1",
        memory_db_path=db_path,
    )
    first_loop.orchestrator.result = replace(first_loop.orchestrator.result, status="BOUNDED", stop_reason="evidence_gap")
    first = first_loop.run(
        "Question", learning_context=context, strategy="research"
    )

    assert first.research_state is not None
    assert first.research_state.adaptive_learning is not None
    assert first.research_state.adaptive_learning.strategy.action == "KEEP"

    # Simulate a process restart: a fresh DecisionLoop has no in-memory
    # history and can only learn from the persisted exact-context observation.
    second_loop = _decision_loop_for_state(
        verification_status="UNVERIFIED",
        lineage_id="or_runtime_persist_2",
        memory_db_path=db_path,
    )
    second_loop.orchestrator.result = replace(second_loop.orchestrator.result, status="BOUNDED", stop_reason="evidence_gap")
    second = second_loop.run(
        "Question", learning_context=context, strategy="research"
    )

    assert second.research_state is not None
    assert second.research_state.adaptive_learning is not None
    adaptive = second.research_state.adaptive_learning
    assert adaptive.strategy.action == "CHANGE"
    assert adaptive.strategy.strategy == "seek_fresh_independent_evidence"

    persisted = second_loop.memory.get_experience_observations(
        context_key="web_research",
        context_conditions=(("freshness", "current"), ("source_count", "2")),
    )
    assert {row["source_cycle_id"] for row in persisted} == {
        "or_runtime_persist_1",
        "or_runtime_persist_2",
    }


def test_re_evaluation_persists_context_and_lineage(tmp_path) -> None:
    db_path = str(tmp_path / "anne.db")
    loop = _decision_loop_for_state(
        verification_status="UNVERIFIED",
        lineage_id="or_reeval_parent",
        memory_db_path=db_path,
    )
    context = {
        "key": "web_research",
        "conditions": {"freshness": "current"},
    }
    loop.orchestrator.result = replace(loop.orchestrator.result, status="BOUNDED", stop_reason="evidence_gap")
    first = loop.run(
        "The answer is supported.",
        learning_context=context,
        strategy="research",
    )
    assert first.research_state is not None
    assert first.research_state.adaptive_learning is not None

    state = first.research_state
    hypothesis = state.hypotheses[0]
    old_id = state.evidence_ledger.record(
        EvidenceLedgerEntry(
            claim=hypothesis.claim,
            source="old",
            provenance="https://old.example/a",
            confidence=0.9,
            passage=hypothesis.claim,
        )
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(old_id, hypothesis.id, "supports")
    )
    state.evidence_ledger.graph.add_node(
        ProvenanceNode("A1", "answer", hypothesis.claim)
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(hypothesis.id, "A1", "derived_from")
    )

    refreshed = loop.research_loop.reassess_after_invalidation(
        state,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
        loop=ReEvaluationLoop(
            research_executor=DerivedResearchExecutor(
                researcher=_FakeReevaluationResearcher()
            )
        ),
    )

    assert refreshed.adaptive_learning is not None
    experience = refreshed.adaptive_learning.experience
    assert experience.context_key == "web_research"
    assert experience.context_conditions == (("freshness", "current"),)
    assert experience.parent_cycle_id == "or_reeval_parent"
    assert experience.lineage == ("or_reeval_parent", experience.source_cycle_id)

    persisted = loop.memory.get_experience_observations(
        context_key="web_research",
        context_conditions=(("freshness", "current"),),
    )
    assert any(
        row["source_cycle_id"] == experience.source_cycle_id
        and row["parent_cycle_id"] == "or_reeval_parent"
        and row["lineage"] == ("or_reeval_parent", experience.source_cycle_id)
        for row in persisted
    )


def test_re_evaluation_preserves_language_corroboration_metacognitive_signal() -> None:
    loop = _decision_loop_for_state(verification_status="UNVERIFIED")
    loop.orchestrator.result.status = "BOUNDED"
    loop.orchestrator.result.stop_reason = "evidence_gap"
    first = loop.run("The answer is supported.")
    assert first.research_state is not None

    state = first.research_state
    hypothesis = state.hypotheses[0]
    old_id = state.evidence_ledger.record(
        EvidenceLedgerEntry(
            claim=hypothesis.claim,
            source="old",
            provenance="https://old.example/a",
            confidence=0.9,
            passage=hypothesis.claim,
        )
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(old_id, hypothesis.id, "supports")
    )
    state.evidence_ledger.graph.add_node(
        ProvenanceNode("A1-language", "answer", hypothesis.claim)
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(hypothesis.id, "A1-language", "derived_from")
    )
    state = type(state)(
        state.plan,
        state.hypotheses,
        state.critic,
        state.synthesis,
        state.decision,
        state.evidence_ledger,
        state.joint_inferences,
        state.derived_hypotheses,
        state.derived_research_plan,
        state.derived_research_result,
        state.derived_verifications,
        state.re_evaluation,
        state.adaptive_learning,
        state.language_check,
        LanguageCorroborationResult(
            decision=LanguageCheckDecision(True, "high ambiguity"),
            verification=LanguageVerificationResult(
                LanguageVerificationStatus.DIVERGENT,
                "Bunu yap",
                source_refs=("bitigci:old", "tdk:old"),
                independent_sources=("bitigci", "tdk"),
                matched_meanings=("meaning-a", "meaning-b"),
                reason="sources diverge",
            ),
        ),
    )

    refreshed = loop.research_loop.reassess_after_invalidation(
        state,
        invalidated_evidence_id=old_id,
        target_node_id="A1-language",
        research_question="Independently re-test the answer",
        loop=ReEvaluationLoop(
            research_executor=DerivedResearchExecutor(
                researcher=_FakeReevaluationResearcher()
            )
        ),
    )

    assert refreshed.adaptive_learning is not None
    assessment = refreshed.adaptive_learning.metacognition
    assert assessment.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert assessment.research_required is False
    assert "language_source_divergence" in assessment.recalibration_triggers
    assert refreshed.adaptive_learning.trace.language_corroboration["status"] == "divergent"
    assert refreshed.adaptive_learning.trace.language_corroboration["authoritative"] is False
    assert refreshed.adaptive_learning.experience.language_corroboration_status == "divergent"
    assert refreshed.adaptive_learning.experience.language_corroboration_providers == ("bitigci", "tdk")
