"""Evidence enforcement: memory is not proof; independent verification is."""
from __future__ import annotations

from anne.core.cognitive_state import Consciousness, Hypothesis
from anne.core.ethic_core import EthicScore
from anne.core.evidence import EvidenceGate
from anne.core.pipeline import AnnePipeline
from anne.memory.fractal_memory import FractalMemory


def make_pipeline(tmp_path):
    return AnnePipeline(FractalMemory(tmp_path / "anne.db"))


def test_missing_evidence_blocks_decision(tmp_path):
    pipeline = make_pipeline(tmp_path)
    state = pipeline.duy("Bu iddianın kanıtı nedir?", [Consciousness(id="user")])
    state = pipeline.bak(state)
    state = pipeline.gor(state, [Hypothesis("h1", "iddia", "Unsupported claim", 0.95)])
    state = pipeline.anla(state, Hypothesis("h1", "iddia", "Unsupported claim", 0.95))
    state = pipeline.yap(state, Hypothesis("h1", "iddia", "Unsupported claim", 0.95))

    assert state.context_map["evidence_gate"] == "blocked"
    assert state.action == "ABSTAIN"
    assert state.output["action"] == "HALT"
    assert state.evidence_status == "missing"


def test_refuted_evidence_never_allows_authoritative_decision():
    assert not EvidenceGate.allows_decision(required=True, status="refuted")
    assert "refuted" in EvidenceGate.reason("refuted").lower()


def test_unverified_memory_does_not_enable_decision(tmp_path):
    pipeline = make_pipeline(tmp_path)
    consciousness = Consciousness(id="user")
    prior = Hypothesis("prior", "kaynak", "Prior source claim", 0.8, source="memory")
    pipeline.memory.save_hypothesis(prior)
    pipeline.memory.save_decision(
        decision_id="prior-decision",
        hyp_id="prior",
        score=EthicScore(0.8, 1.0, 0.1, 0.85, "ONAYLA"),
        consciousnesses=[consciousness],
        stage="YAP",
        task_mode="general",
    )

    state = pipeline.duy("Kaynağı nedir?", [consciousness])
    state = pipeline.bak(state)
    hypothesis = Hypothesis("h1", "kaynak", "Prior source claim", 0.95, source="memory")
    state = pipeline.gor(state, [hypothesis])
    state = pipeline.anla(state, hypothesis)
    state = pipeline.yap(state, hypothesis)

    assert state.evidence_status == "unverified"
    assert state.evidence_verified is False
    assert state.context_map["evidence_gate"] == "blocked"
    assert state.action == "ABSTAIN"


def test_non_evidence_request_preserves_existing_decision_path(tmp_path):
    pipeline = make_pipeline(tmp_path)
    state = pipeline.duy("Merhaba Anne", [Consciousness(id="user")])
    state = pipeline.bak(state)
    hypothesis = Hypothesis("h1", "greeting", "Hello", 0.95)
    state = pipeline.gor(state, [hypothesis])
    state = pipeline.anla(state, hypothesis)

    assert state.context_map["evidence_gate"] == "passed"
    assert state.ethic_score is not None


def test_independently_verified_evidence_allows_decision(tmp_path):
    """Only independent verification (not memory/search) may yield AVAILABLE."""
    from anne.core.verification import ReferenceClaim, ReferenceVerifier

    claim = "The capital of France is Paris."
    verifier = ReferenceVerifier(
        (
            ReferenceClaim(claim=claim, source="atlas:geo-1", supported=True),
        )
    )
    pipeline = AnnePipeline(FractalMemory(tmp_path / "anne.db"), claim_verifier=verifier)
    state = pipeline.duy("What is the capital of France? Provide evidence.", [Consciousness(id="user")])
    if not state.requires_evidence:
        state.requires_evidence = True
    state = pipeline.bak(state)
    hyp = Hypothesis("h1", "geo", claim, 0.9)
    state = pipeline.gor(state, [hyp])
    state = pipeline.anla(state, hyp)

    assert state.evidence_status == "available"
    assert state.evidence_verified is True
    assert state.context_map.get("evidence_gate") == "passed"


def test_refuted_independent_verification_blocks(tmp_path):
    from anne.core.verification import ReferenceClaim, ReferenceVerifier

    claim = "The capital of France is Berlin."
    verifier = ReferenceVerifier(
        (ReferenceClaim(claim=claim, source="atlas:geo-1", supported=False),)
    )
    pipeline = AnnePipeline(FractalMemory(tmp_path / "anne.db"), claim_verifier=verifier)
    state = pipeline.duy("Is Berlin the capital of France? Evidence?", [Consciousness(id="user")])
    state.requires_evidence = True
    state = pipeline.bak(state)
    hyp = Hypothesis("h1", "geo", claim, 0.9)
    state = pipeline.gor(state, [hyp])
    state = pipeline.anla(state, hyp)
    assert state.evidence_status == "refuted"
    assert state.context_map.get("evidence_gate") == "blocked"


def test_conflicting_independent_verification_blocks(tmp_path):
    from anne.core.verification import ReferenceClaim, ReferenceVerifier

    claim = "Widget X costs 10 USD."
    verifier = ReferenceVerifier(
        (
            ReferenceClaim(claim=claim, source="src-a", supported=True),
            ReferenceClaim(claim=claim, source="src-b", supported=False),
        )
    )
    pipeline = AnnePipeline(FractalMemory(tmp_path / "anne.db"), claim_verifier=verifier)
    state = pipeline.duy("Price of Widget X with evidence?", [Consciousness(id="user")])
    state.requires_evidence = True
    state = pipeline.bak(state)
    hyp = Hypothesis("h1", "price", claim, 0.9)
    state = pipeline.anla(state, hyp)
    assert state.evidence_status == "conflicting"
    assert not EvidenceGate.allows_decision(required=True, status=state.evidence_status)


def test_verification_exception_stays_blocked(tmp_path):
    class Boom:
        def verify(self, claim: str):
            raise RuntimeError("verifier exploded")

    pipeline = AnnePipeline(FractalMemory(tmp_path / "anne.db"), claim_verifier=Boom())
    state = pipeline.duy("Evidence for claim Z?", [Consciousness(id="user")])
    state.requires_evidence = True
    state = pipeline.bak(state)
    hyp = Hypothesis("h1", "z", "claim Z", 0.9)
    state = pipeline.anla(state, hyp)
    assert state.evidence_status in {"unverified", "missing"}
    assert state.context_map.get("evidence_gate") == "blocked"


def test_mapping_verified_without_sources_is_not_available():
    from anne.core.evidence import evidence_status_from_verification
    from anne.core.verification import FactualStatus, VerificationResult
    from anne.core.requirements import EvidenceStatus

    bad = VerificationResult(status=FactualStatus.VERIFIED, sources=(), reason="no sources")
    assert evidence_status_from_verification(bad) is EvidenceStatus.UNVERIFIED
