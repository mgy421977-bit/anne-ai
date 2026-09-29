from dataclasses import replace

from anne.core.verification import FactualStatus
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.evidence import EvidenceItem, EvidenceLedgerEntry
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop
from anne.learning.reevaluation_loop import ReEvaluationLoop


class FakeResearcher:
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


def test_cognitive_loop_reenters_synthesis_after_invalidation() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("The answer is supported.")

    old_id = state.evidence_ledger.record(
        EvidenceLedgerEntry(
            claim="The answer is supported.",
            source="old",
            provenance="https://old.example/a",
            confidence=0.9,
            passage="The answer is supported.",
        )
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(old_id, "H1", "supports")
    )
    state.evidence_ledger.graph.add_node(
        ProvenanceNode("A1", "answer", "The answer is supported.")
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge("H1", "A1", "derived_from")
    )

    refreshed = loop.reassess_after_invalidation(
        state,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
        loop=ReEvaluationLoop(
            research_executor=DerivedResearchExecutor(researcher=FakeResearcher())
        ),
    )

    assert refreshed.re_evaluation is not None
    assert refreshed.re_evaluation.verification is not None
    assert refreshed.re_evaluation.verification.status is FactualStatus.VERIFIED
    assert refreshed.synthesis.reason
    assert refreshed.evidence_ledger.graph.get(old_id).status.value == "invalidated"
    assert refreshed.evidence_ledger.graph.get("A1").status.value == "stale"

    replacement = refreshed.re_evaluation.rebuild
    assert replacement is not None
    assert refreshed.evidence_ledger.graph.get(replacement.replacement_node).status.value == "active"

    # Re-synthesis uses fresh evidence but does not rewrite ledger history.
    statuses = [
        entry["status"] for entry in refreshed.evidence_ledger.as_dict()["entries"]
    ]
    assert all(status == "unverified" for status in statuses)


def test_cognitive_loop_keeps_state_when_research_plan_cannot_reactivate() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("The answer is supported.")
    old_id = state.evidence_ledger.record(
        EvidenceLedgerEntry(
            claim="Old claim",
            source="old",
            provenance="https://old.example/a",
            confidence=0.9,
            passage="Old source",
        )
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge(old_id, "H1", "supports")
    )
    state.evidence_ledger.graph.add_node(
        ProvenanceNode("A1", "answer", "The answer is supported.")
    )
    state.evidence_ledger.graph.add_edge(
        ProvenanceEdge("H1", "A1", "derived_from")
    )

    class UnclearResearcher:
        def research(self, query: str) -> list[EvidenceItem]:
            return [
                EvidenceItem(
                    source="source-a",
                    claim="unrelated",
                    kind="web",
                    provenance="https://alpha.example/a",
                    confidence=0.9,
                    passage="No direct support.",
                ),
                EvidenceItem(
                    source="source-b",
                    claim="unrelated",
                    kind="web",
                    provenance="https://beta.example/b",
                    confidence=0.9,
                    passage="Still unclear.",
                ),
            ]

    refreshed = loop.reassess_after_invalidation(
        state,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
        loop=ReEvaluationLoop(
            research_executor=DerivedResearchExecutor(researcher=UnclearResearcher())
        ),
    )

    assert refreshed.re_evaluation is not None
    assert refreshed.re_evaluation.rebuild is None
    assert refreshed.evidence_ledger.graph.get("A1").status.value == "stale"
