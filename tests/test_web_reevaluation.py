from anne.learning.evidence import (
    EvidenceItem,
    EvidenceLedger,
    EvidenceLedgerEntry,
)
from anne.learning.web_reevaluation import BoundedWebReEvaluator


class FakeResearcher:
    def __init__(self, items):
        self.items = tuple(items)
        self.calls = []

    def research(self, query):
        self.calls.append(query)
        return self.items


def _ledger_with_downstream_dependency():
    ledger = EvidenceLedger()
    evidence_id = ledger.record(
        EvidenceLedgerEntry(
            claim="Original claim",
            source="source-a",
            provenance="https://a.example/source",
            confidence=0.8,
            passage="Original claim",
        )
    )
    ledger.register_claim(
        claim_id="H1",
        claim="Original claim",
        evidence_ids=(evidence_id,),
    )
    ledger.register_derivation(
        source_id="H1",
        source_kind="hypothesis",
        target_id="SYNTHESIS",
        target_kind="decision_synthesis",
        target_content="Original synthesis",
        relation="informs",
    )
    return ledger, evidence_id


def _fresh_item(source, provenance, support="supports"):
    return EvidenceItem(
        source=source,
        claim="Original claim",
        kind="web",
        provenance=provenance,
        confidence=0.9,
        passage="Original claim",
        support=support,
    )


def test_explicit_invalidation_triggers_one_bounded_fresh_research():
    ledger, evidence_id = _ledger_with_downstream_dependency()
    researcher = FakeResearcher((_fresh_item("source-b", "https://b.example/source"),))

    result = BoundedWebReEvaluator(researcher).reevaluate(
        question="Original claim",
        ledger=ledger,
        evidence_id=evidence_id,
    )

    assert result.plan.action == "RESEARCH"
    assert result.plan.invalidated_node == evidence_id
    assert result.plan.stale_nodes == ("H1", "SYNTHESIS")
    assert researcher.calls == ["Original claim"]
    assert len(result.fresh_evidence) == 1
    assert result.verification.status.value == "unverified"
    assert result.refreshed_state is None
    assert ledger.status(evidence_id).value == "invalidated"
    assert ledger.status("H1").value == "stale"
    assert ledger.status("SYNTHESIS").value == "stale"


def test_re_evaluation_does_not_research_when_no_downstream_result():
    ledger = EvidenceLedger()
    evidence_id = ledger.record(
        EvidenceLedgerEntry(
            claim="Orphan claim",
            source="source-a",
            provenance="https://a.example/orphan",
            confidence=0.8,
        )
    )
    researcher = FakeResearcher(())

    result = BoundedWebReEvaluator(researcher).reevaluate(
        question="Orphan claim",
        ledger=ledger,
        evidence_id=evidence_id,
    )

    assert result.plan.action == "STOP"
    assert result.fresh_evidence == ()
    assert researcher.calls == []


def test_re_evaluation_research_is_bounded_to_one_query():
    ledger, evidence_id = _ledger_with_downstream_dependency()
    researcher = FakeResearcher((_fresh_item("source-b", "https://b.example/source"),))

    result = BoundedWebReEvaluator(researcher).reevaluate(
        question="Original claim",
        ledger=ledger,
        evidence_id=evidence_id,
    )

    assert result.queries_used == 1
    assert result.sources_used == 1
    assert len(researcher.calls) == 1


def test_re_evaluation_requires_two_independent_sources_before_refresh():
    ledger, evidence_id = _ledger_with_downstream_dependency()
    researcher = FakeResearcher(
        (
            _fresh_item("source-b", "https://b.example/source"),
            _fresh_item("source-c", "https://c.example/source"),
        )
    )

    result = BoundedWebReEvaluator(researcher).reevaluate(
        question="Original claim",
        ledger=ledger,
        evidence_id=evidence_id,
    )

    assert result.verification.status.value == "verified"
    assert result.verification.sources == (
        "https://b.example/source",
        "https://c.example/source",
    )
    assert result.refreshed_state is not None
    assert result.refreshed_state.decision.action == "PROCEED"


def test_re_evaluation_does_not_refresh_from_one_contradicting_source():
    ledger, evidence_id = _ledger_with_downstream_dependency()
    researcher = FakeResearcher(
        (_fresh_item("source-b", "https://b.example/source", "contradicts"),)
    )

    result = BoundedWebReEvaluator(researcher).reevaluate(
        question="Original claim",
        ledger=ledger,
        evidence_id=evidence_id,
    )

    assert result.verification.status.value == "unverified"
    assert result.refreshed_state is None
