from anne.core.cognitive_state import Consciousness
from anne.core.decision_loop import DecisionLoop
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.agent_swarm import AgentRole, EvidenceItem, EvidencePackage


def evidence_package() -> EvidencePackage:
    return EvidencePackage(
        mission_id="mission_test",
        agent_id="agent_test",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim="kaynak nedir?",
                source="https://example.com/source",
                evidence_kind="WEB_SOURCE",
                provenance="MITOS:test",
            ),
        ),
    )


def test_evidence_request_without_package_is_blocked_as_missing():
    loop = DecisionLoop(memory=FractalMemory(":memory:"))
    result = loop.run(
        raw_input="Kaynak nedir?",
        parties=[Consciousness(id="user")],
    )
    assert result.state is not None
    assert result.state.evidence_status == "missing"
    assert result.verdict == "ABSTAIN"


def test_evidence_package_does_not_bypass_verification():
    loop = DecisionLoop(memory=FractalMemory(":memory:"))
    result = loop.run(
        raw_input="Kaynak nedir?",
        parties=[Consciousness(id="user")],
        evidence_packages=[evidence_package()],
    )
    assert result.state is not None
    assert result.state.evidence_status == "unverified"
    assert result.state.evidence_verified is False
    assert result.verdict == "ABSTAIN"
