from anne.core.verification import FactualStatus
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.evidence import EvidenceItem, EvidenceLedger, EvidenceLedgerEntry
from anne.learning.provenance_graph import ProvenanceEdge, ProvenanceNode
from anne.learning.reevaluation_loop import ReEvaluationLoop


class FakeResearcher:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def research(self, query: str) -> list[EvidenceItem]:
        self.queries.append(query)
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


def test_re_evaluation_researches_verifies_and_rebuilds_without_deleting_history() -> None:
    ledger, old_id = _ledger()
    researcher = FakeResearcher()
    loop = ReEvaluationLoop(
        research_executor=DerivedResearchExecutor(researcher=researcher)
    )

    result = loop.run(
        ledger,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
    )

    assert result.plan.action == "RESEARCH"
    assert result.verification is not None
    assert result.verification.status is FactualStatus.VERIFIED
    assert result.reactivated is True
    assert result.rebuild is not None
    assert result.rebuild.replacement_node.startswith("A1:re")

    assert ledger.graph.get(old_id).status.value == "invalidated"
    assert ledger.graph.get("H1").status.value == "stale"
    assert ledger.graph.get("A1").status.value == "stale"
    assert ledger.graph.get(result.rebuild.replacement_node).status.value == "active"

    statuses = [entry["status"] for entry in ledger.as_dict()["entries"]]
    assert all(status == "unverified" for status in statuses)
    assert researcher.queries == ["Independently re-test the answer"]


def test_re_evaluation_does_not_reactivate_on_conflicting_evidence() -> None:
    ledger, old_id = _ledger()

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

    result = ReEvaluationLoop(
        research_executor=DerivedResearchExecutor(researcher=ConflictingResearcher())
    ).run(
        ledger,
        invalidated_evidence_id=old_id,
        target_node_id="A1",
        research_question="Independently re-test the answer",
    )

    assert result.verification is not None
    assert result.verification.status is FactualStatus.CONFLICTING
    assert result.rebuild is None
    assert ledger.graph.get("A1").status.value == "stale"


def test_re_evaluation_requires_explicit_stale_target() -> None:
    ledger, old_id = _ledger()

    try:
        ReEvaluationLoop().run(
            ledger,
            invalidated_evidence_id=old_id,
            target_node_id="E_NOT_STALE",
            research_question="test",
        )
    except ValueError as exc:
        assert "stale downstream" in str(exc)
        assert ledger.graph.get(old_id).status.value == "active"
    else:
        raise AssertionError("re-evaluation must not select a target implicitly")
