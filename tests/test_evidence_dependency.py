from anne.learning.evidence import EvidenceDependency


def test_dependency_requires_claim_and_evidence_ids() -> None:
    dep = EvidenceDependency("C1", "Paris is the capital of France.", ("E1", "E2"))
    assert dep.evidence_ids == ("E1", "E2")


def test_dependency_rejects_empty_evidence_ids() -> None:
    try:
        EvidenceDependency("C1", "claim", ())
    except ValueError as exc:
        assert "evidence_ids" in str(exc)
    else:
        raise AssertionError("empty dependency set must fail closed")
