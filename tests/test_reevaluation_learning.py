from anne.core.trace import CycleTrace
from anne.learning.adaptive_learning import AdaptiveLearningCoordinator
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.experience_learning import ExperienceLearner
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.reevaluation_learning import ReEvaluationLearningAdapter
from anne.learning.reevaluation_loop import ReEvaluationLoop
from anne.learning.strategy_adaptation import StrategyAdapter


def _ledger() -> tuple[EvidenceLedger, str]:
    ledger = EvidenceLedger()
    old_id = ledger.record(
        EvidenceLedgerEntry(
            claim="Old claim",
            source="old",
            provenance="https://old.example/source",
            confidence=0.9,
            passage="Old source passage",
        )
    )
    ledger.graph.add_node(
        ProvenanceNode("H1", "claim", "The replacement claim is supported.")
    )
    ledger.graph.add_node(
        ProvenanceNode("A1", "answer", "The replacement claim is supported.")
    )
    ledger.graph.add_edge(ProvenanceEdge(old_id, "H1", "supports"))
    ledger.graph.add_edge(ProvenanceEdge("H1", "A1", "derived_from"))
    return ledger, old_id


class ConflictingResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        claim = "The replacement claim is supported."
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
                passage=f"{claim} is not true.",
            ),
        ]


class SuccessfulResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        claim = "The replacement claim is supported."
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


class EmptyResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        return []


def _run(researcher: object):
    ledger, old_id = _ledger()
    cycle = ReEvaluationLoop(
        research_executor=DerivedResearchExecutor(researcher=researcher)
    ).run(
        ledger,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
    )
    return ReEvaluationLearningAdapter().to_trace(
        cycle,
        cycle_id="reeval-test",
        strategy="research",
    )


def test_conflicting_re_evaluation_becomes_factual_failure_learning() -> None:
    trace = _run(ConflictingResearcher())
    experience = ExperienceLearner().from_trace(trace, strategy="research")

    assert trace.stop_reason == "reevaluation_conflict"
    assert trace.decision["status"] == "REVIEW"
    assert experience.outcome == "FAILURE"
    assert experience.failure_class == "factual"
    assert experience.safe_to_reuse is False


def test_two_conflicting_re_evaluations_trigger_bounded_independent_recheck() -> None:
    traces = (
        _run(ConflictingResearcher()),
        _run(ConflictingResearcher()),
    )
    learner = ExperienceLearner()
    experiences = tuple(
        learner.from_trace(trace, strategy="research") for trace in traces
    )

    decision = StrategyAdapter().adapt("research", experiences)

    assert decision.action == "CHANGE"
    assert decision.strategy == "recheck_independent_evidence"
    assert decision.source_cycle_ids == ("reeval-test", "reeval-test")


def test_insufficient_fresh_evidence_is_distinguished_from_conflict() -> None:
    trace = _run(EmptyResearcher())
    experience = ExperienceLearner().from_trace(trace, strategy="research")

    assert trace.stop_reason == "reevaluation_insufficient_evidence"
    assert experience.failure_class == "evidence_gap"


def test_repeated_success_does_not_escalate_strategy() -> None:
    traces = (
        _run(SuccessfulResearcher()),
        _run(SuccessfulResearcher()),
    )
    learner = ExperienceLearner()
    experiences = tuple(
        learner.from_trace(trace, strategy="research") for trace in traces
    )

    decision = StrategyAdapter().adapt("research", experiences)

    assert decision.action == "KEEP"
    assert decision.strategy == "research"


def test_adaptive_coordinator_keeps_re_evaluation_non_authoritative() -> None:
    trace = _run(ConflictingResearcher())
    result = AdaptiveLearningCoordinator().observe(trace, strategy="execute")

    assert result.experience.safe_to_reuse is False
    assert result.strategy.action == "KEEP"
    assert trace.decision["status"] == "REVIEW"
    assert trace.decision["status"] != "EXECUTE"
