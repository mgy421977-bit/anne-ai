from __future__ import annotations

from anne import AnneRequest, AnneRuntime
from anne.agent.runtime import AnneAgent
from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate, Authorization
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
from anne.memory.local_memory import LocalMemory
from anne.providers.local import LocalProvider


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


def _tool_agent(tmp_path):
    return AnneAgent(
        LocalProvider(),
        LocalMemory(":memory:"),
        workspace=tmp_path,
        decision_loop=DecisionLoop(memory=FractalMemory(":memory:")),
    )


def test_agent_tool_deny_and_review_never_execute(tmp_path, monkeypatch) -> None:
    agent = _tool_agent(tmp_path)
    calls: list[dict[str, str]] = []
    agent.tools["local_read"] = lambda **arguments: calls.append(arguments)
    for decision in (ActionDecision.DENY, ActionDecision.REVIEW):
        monkeypatch.setattr(
            agent.agency_gate,
            "authorize",
            lambda *args, decision=decision, **kwargs: Authorization(
                decision, "test gate"
            ),
        )
        result = agent._execute_tool("local_read", {"path": "sample.txt"})
        assert result["ok"] is False
        assert result["human_review_required"] is (decision is ActionDecision.REVIEW)
        assert not calls


def test_agent_tool_allow_executes_only_after_gate(tmp_path) -> None:
    agent = _tool_agent(tmp_path)
    calls: list[dict[str, str]] = []
    agent.tools["local_read"] = lambda **arguments: calls.append(arguments) or "content"
    result = agent._execute_tool("local_read", {"path": "sample.txt"})

    assert result == {"ok": True, "result": "content"}
    assert calls == [{"path": "sample.txt"}]


def test_agent_tool_proposal_has_explicit_safe_context(tmp_path) -> None:
    agent = _tool_agent(tmp_path)
    captured: list[ActionProposal] = []
    original = agent.agency_gate.authorize

    def capture(proposal, **kwargs):
        captured.append(proposal)
        return original(proposal, **kwargs)

    agent.agency_gate.authorize = capture  # type: ignore[method-assign]
    agent.tools["local_read"] = lambda **arguments: "content"
    assert agent._execute_tool("local_read", {"path": "sample.txt"})["ok"]
    assert captured[0].risk == 0.10
    assert captured[0].reversible is True


def test_unknown_risk_and_reversibility_fail_closed() -> None:
    gate = AgencyGate()
    assert gate.authorize(
        ActionProposal("x", provenance=("source",)), safety_allowed=True
    ).decision is ActionDecision.DENY
    assert gate.authorize(
        ActionProposal("x", risk=0.1, reversible=None, provenance=("source",)),
        safety_allowed=True,
    ).decision is ActionDecision.DENY


def test_retry_preserves_evidence_requirement_and_unverified_status(tmp_path) -> None:
    verifier = ReferenceVerifier((ReferenceClaim("different claim", "ref:1", True),))
    result = DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")).run_cognitive(
        "Bu iddianın kanıtı nedir?",
        seed=7,
        verifier=verifier,
    )

    assert result.retry_count == 1
    assert result.state is not None
    assert result.state.requires_evidence is True
    assert result.state.evidence_status != EvidenceStatus.AVAILABLE.value
    assert result.state.output.get("factual_status") != "verified"


def test_retry_with_independent_verification_can_reach_available(tmp_path) -> None:
    claim = "The capital of France is Paris."
    verifier = ReferenceVerifier((ReferenceClaim(claim, "atlas:1", True),))
    result = DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")).run(
        "Bu iddianın kanıtı nedir?",
        claim=claim,
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.requires_evidence is True
    assert result.state.evidence_status == EvidenceStatus.AVAILABLE.value
    assert result.output["factual_status"] == "verified"


def test_retry_reverifies_before_available_transition(tmp_path) -> None:
    class SequencedVerifier:
        def __init__(self) -> None:
            self.calls = 0

        def verify(self, claim: str) -> VerificationResult:
            self.calls += 1
            if self.calls == 1:
                return VerificationResult(FactualStatus.UNVERIFIED)
            return VerificationResult(FactualStatus.VERIFIED, ("independent:retry",))

    verifier = SequencedVerifier()
    result = DecisionLoop(memory=FractalMemory(tmp_path / "anne.db")).run_cognitive(
        "Bu iddianın kanıtı nedir?",
        seed=7,
        verifier=verifier,
    )

    assert verifier.calls >= 2
    assert result.retry_count == 1
    assert result.state is not None
    assert result.state.requires_evidence is True
    assert result.state.evidence_status == EvidenceStatus.AVAILABLE.value
    assert result.state.output["factual_status"] == "verified"
