from anne.learning.evidence import EvidenceLedger, EvidenceLedgerEntry, EvidenceStatus


def test_ledger_exposes_re_evaluation_plan() -> None:
    ledger = EvidenceLedger()
    evidence_id = ledger.record(
        EvidenceLedgerEntry(
            claim="claim",
            source="source",
            provenance="https://example.test/evidence",
            confidence=0.9,
            status=EvidenceStatus.VERIFIED,
            passage="source passage",
        )
    )
    ledger.register_claim(
        claim_id="C1",
        claim="claim",
        evidence_ids=(evidence_id,),
    )
    plan = ledger.re_evaluation_plan(evidence_id)

    assert plan.requires_research is True
    assert plan.stale_nodes == ("C1",)
