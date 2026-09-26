from __future__ import annotations

from anne import AnneRequest, AnneRuntime
from anne.core.cognitive_state import Consciousness
from anne.core.decision_loop import DecisionLoop
from anne.core.evidence import evidence_status_from_verification
from anne.core.pipeline import AnnePipeline
from anne.core.requirements import EvidenceStatus
from anne.core.verification import (
    FactualStatus,
    ReferenceClaim,
    ReferenceVerifier,
    VerificationResult,
)
from anne.memory.fractal_memory import FractalMemory


def test_verified_transition_requires_provenance() -> None:
    verified = VerificationResult(FactualStatus.VERIFIED, ("independent:1",))
    missing_provenance = VerificationResult(FactualStatus.VERIFIED, ())

    assert evidence_status_from_verification(verified) is EvidenceStatus.AVAILABLE
    assert evidence_status_from_verification(missing_provenance) is EvidenceStatus.UNVERIFIED
    assert evidence_status_from_verification(
        VerificationResult(FactualStatus.CONFLICTING, ("a", "b"))
    ) is EvidenceStatus.CONFLICTING
    assert evidence_status_from_verification(
        VerificationResult(FactualStatus.REFUTED, ("a",))
    ) is EvidenceStatus.REFUTED


def test_pipeline_uses_independent_verification_before_decision(tmp_path) -> None:
    claim = "The capital of France is Paris."
    verifier = ReferenceVerifier((ReferenceClaim(claim, "atlas:1", True),))
    pipeline = AnnePipeline(
        FractalMemory(tmp_path / "anne.db"),
        claim_verifier=verifier,
    )
    state = pipeline.duy("Bu iddianın kanıtı nedir?", [Consciousness(id="user")])
    state = pipeline.bak(state)
    hypothesis = type(
        "HypothesisLike",
        (),
        {
            "id": "h1",
            "topic": "capital",
            "claim": claim,
            "probability": 0.9,
            "source": "MITOS:UNVERIFIED",
        },
    )()
    state = pipeline.gor(state, [hypothesis])
    state = pipeline.anla(state, hypothesis)

    assert state.evidence_status == EvidenceStatus.AVAILABLE.value
    assert state.evidence_verified is True
    assert state.context_map["verification_status"] == FactualStatus.VERIFIED.value
    assert state.context_map["evidence_gate"] == "passed"


def test_mitos_candidate_remains_non_authoritative(tmp_path) -> None:
    result = DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")).run_cognitive(
        "Explore a bounded technical option",
        seed=7,
    )

    assert result.selection is not None
    assert result.selection.candidate is not None
    assert result.selection.candidate.evidence_status == "SIMULATION"
    assert result.state is not None
    assert result.state.output["candidate_evidence_status"] == "SIMULATION"
    assert result.state.output["factual_status"] == "unverified"


def test_canonical_runtime_human_review_never_becomes_allow(tmp_path) -> None:
    runtime = AnneRuntime(DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")))
    result = runtime.handle(AnneRequest("Benim adıma hemen gerçekleştir"))

    assert result.status == "ABORTED"
    assert result.verdict == "REVIEW"
    assert result.output["agency_decision"] == "REVIEW"
    assert result.output["human_review_required"] is True


def test_canonical_runtime_delegates_to_decision_loop(tmp_path) -> None:
    runtime = AnneRuntime(DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")))
    result = runtime.handle(AnneRequest("Merhaba ANNE"))

    assert result.fail_fast is not None
    assert result.fail_fast["passed"] is True
    assert result.verdict in {"ONAYLA", "REVIEW", "REDDET"}
