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

def test_mitos_package_passes_only_after_independent_atomic_verification():
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    package = EvidencePackage(
        mission_id="mission_panel",
        agent_id="agent_mitos",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim="655 W panel Türkiye'de 4.800 TL",
                source="https://example.com/panel",
                evidence_kind="WEB_SOURCE",
                confidence=0.9,
                provenance="MITOS:web_research",
            ),
            EvidenceItem(
                claim="şu anda satışta",
                source="https://example.com/stock",
                evidence_kind="WEB_SOURCE",
                confidence=0.9,
                provenance="MITOS:web_research",
            ),
        ),
    )
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/panel",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                True,
                "official",
            ),
            SourceRecord(
                "https://example.com/stock",
                "şu anda satışta",
                "TR",
                date.today(),
                True,
                "official",
            ),
        ),
        required_scope="TR",
        allowed_authorities=("official",),
        max_age_days=365,
    )

    loop = DecisionLoop(memory=FractalMemory(":memory:"))
    result = loop.run(
        raw_input="655 W panel Türkiye'de 4.800 TL ve şu anda satışta mı?",
        claim="655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "available"
    assert result.state.evidence_verified is True
    assert result.state.context_map["evidence_gate"] == "passed"
