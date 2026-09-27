from anne.learning.evidence import EvidenceLedger, EvidenceLedgerEntry, EvidenceStatus
from anne.learning.provenance_graph import NodeStatus


def _entry() -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        claim="Paris is the capital of France.",
        source="source-a",
        provenance="https://example.test/paris",
        confidence=0.9,
        status=EvidenceStatus.VERIFIED,
        passage="Paris is the capital of France.",
    )


def test_ledger_records_evidence_and_registers_explicit_claim_dependency() -> None:
    ledger = EvidenceLedger()
    evidence_id = ledger.record(_entry())
    ledger.register_claim(
        claim_id="C1",
        claim="Paris is the capital of France.",
        evidence_ids=(evidence_id,),
    )

    assert ledger.get(evidence_id).status is EvidenceStatus.VERIFIED
    assert ledger.status(evidence_id) is NodeStatus.ACTIVE
    assert ledger.status("C1") is NodeStatus.ACTIVE


def test_invalidating_evidence_marks_claim_stale_through_ledger() -> None:
    ledger = EvidenceLedger()
    evidence_id = ledger.record(_entry())
    ledger.register_claim(
        claim_id="C1",
        claim="Paris is the capital of France.",
        evidence_ids=(evidence_id,),
    )
    ledger.register_derivation(
        source_id="C1",
        source_kind="claim",
        target_id="H1",
        target_kind="hypothesis",
        target_content="Working hypothesis",
    )
    ledger.register_derivation(
        source_id="H1",
        source_kind="hypothesis",
        target_id="A1",
        target_kind="answer",
        target_content="Working answer",
    )

    affected = ledger.invalidate_evidence(evidence_id)

    assert affected == (evidence_id, "C1", "H1", "A1")
    assert ledger.status(evidence_id) is NodeStatus.INVALIDATED
    assert ledger.status("C1") is NodeStatus.STALE
    assert ledger.status("H1") is NodeStatus.STALE
    assert ledger.status("A1") is NodeStatus.STALE


def test_unknown_evidence_dependency_fails_closed() -> None:
    ledger = EvidenceLedger()
    try:
        ledger.register_claim(
            claim_id="C1",
            claim="claim",
            evidence_ids=("missing",),
        )
    except ValueError as exc:
        assert "unknown evidence id" in str(exc)
    else:
        raise AssertionError("unknown evidence dependency must fail closed")
