from anne.core.source_independence import SourceIndependenceStatus
from anne.learning.evidence import EvidenceLedger, EvidenceLedgerEntry, EvidenceStatus
from anne.learning.joint_inference import JointInferenceEngine, JointInferenceStatus


def _ledger(*entries: EvidenceLedgerEntry) -> tuple[EvidenceLedger, tuple[str, ...]]:
    ledger = EvidenceLedger()
    ids = tuple(ledger.record(entry) for entry in entries)
    return ledger, ids


def test_joint_inference_combines_verified_premises_without_granting_authority() -> None:
    ledger, ids = _ledger(
        EvidenceLedgerEntry(
            claim="A implies X",
            source="source-a",
            provenance="https://alpha.example/a",
            confidence=0.9,
            status=EvidenceStatus.VERIFIED,
        ),
        EvidenceLedgerEntry(
            claim="B implies X",
            source="source-b",
            provenance="https://beta.example/b",
            confidence=0.8,
            status=EvidenceStatus.VERIFIED,
        ),
    )

    result = JointInferenceEngine().infer(
        claim="A and B jointly support X",
        evidence_ids=ids,
        ledger=ledger,
    )

    assert result.status == JointInferenceStatus.DERIVED
    assert result.verified_premises == 2
    assert result.source_independence.status == SourceIndependenceStatus.MULTIPLE_PUBLISHER_FAMILIES
    assert "authority" in result.reason


def test_joint_inference_does_not_upgrade_unverified_premises() -> None:
    ledger, ids = _ledger(
        EvidenceLedgerEntry(
            claim="premise",
            source="source-a",
            provenance="https://alpha.example/a",
            confidence=1.0,
        ),
        EvidenceLedgerEntry(
            claim="premise",
            source="source-b",
            provenance="https://beta.example/b",
            confidence=1.0,
            status=EvidenceStatus.VERIFIED,
        ),
    )

    result = JointInferenceEngine().infer(
        claim="derived claim",
        evidence_ids=ids,
        ledger=ledger,
    )

    assert result.status == JointInferenceStatus.UNVERIFIED_PREMISES
    assert result.unverified_premises == 1


def test_joint_inference_preserves_conflict() -> None:
    ledger, ids = _ledger(
        EvidenceLedgerEntry(
            claim="premise one",
            source="source-a",
            provenance="https://alpha.example/a",
            confidence=0.8,
            status=EvidenceStatus.VERIFIED,
        ),
        EvidenceLedgerEntry(
            claim="premise two",
            source="source-b",
            provenance="https://beta.example/b",
            confidence=0.8,
            status=EvidenceStatus.CONFLICTING,
        ),
    )

    result = JointInferenceEngine().infer(
        claim="derived claim",
        evidence_ids=ids,
        ledger=ledger,
    )

    assert result.status == JointInferenceStatus.CONFLICTING_PREMISES
    assert result.conflicting_premises == 1


def test_joint_inference_reports_unknown_source_relationship() -> None:
    ledger, ids = _ledger(
        EvidenceLedgerEntry(
            claim="premise one",
            source="source-a",
            provenance="not-a-url",
            confidence=0.8,
            status=EvidenceStatus.VERIFIED,
        ),
        EvidenceLedgerEntry(
            claim="premise two",
            source="source-b",
            provenance="https://beta.example/b",
            confidence=0.8,
            status=EvidenceStatus.VERIFIED,
        ),
    )

    result = JointInferenceEngine().infer(
        claim="derived claim",
        evidence_ids=ids,
        ledger=ledger,
    )

    assert result.source_independence.status == SourceIndependenceStatus.UNKNOWN
