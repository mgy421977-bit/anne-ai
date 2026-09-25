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
        raw_input="655 W panel Türkiye'de 4.800 TL ve şu anda satışta mı? Kaynağı nedir?",
        claim="655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "available"
    assert result.state.evidence_verified is True
    assert result.state.context_map["evidence_gate"] == "passed"



def test_one_unverified_atomic_claim_blocks_pipeline():
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
                provenance="MITOS:web_research",
            ),
            EvidenceItem(
                claim="şu anda satışta",
                source="https://example.com/stock",
                evidence_kind="WEB_SOURCE",
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
        ),
        required_scope="TR",
        allowed_authorities=("official",),
        max_age_days=365,
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input="655 W panel Türkiye'de 4.800 TL ve şu anda satışta mı? Kaynağı nedir?",
        claim="655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "unverified"
    assert result.state.evidence_verified is False
    assert result.state.context_map["evidence_gate"] == "blocked"
    assert result.verdict == "ABSTAIN"


def test_conflicting_atomic_source_blocks_pipeline():
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    package = EvidencePackage(
        mission_id="mission_panel",
        agent_id="agent_mitos",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim="655 W panel Türkiye'de 4.800 TL",
                source="https://example.com/source-a",
                evidence_kind="WEB_SOURCE",
                provenance="MITOS:web_research",
            ),
            EvidenceItem(
                claim="şu anda satışta",
                source="https://example.com/stock",
                evidence_kind="WEB_SOURCE",
                provenance="MITOS:web_research",
            ),
        ),
    )
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/source-a",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                True,
                "official",
            ),
            SourceRecord(
                "https://example.com/source-b",
                "655 W panel Türkiye'de 4.800 TL",
                "TR",
                date.today(),
                False,
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

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input="655 W panel Türkiye'de 4.800 TL ve şu anda satışta mı? Kaynağı nedir?",
        claim="655 W panel Türkiye'de 4.800 TL ve şu anda satışta",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "conflicting"
    assert result.state.evidence_verified is False
    assert result.state.context_map["evidence_gate"] == "blocked"
    assert result.verdict == "ABSTAIN"


def test_stale_atomic_source_blocks_current_claim():
    from datetime import date, timedelta
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    package = evidence_package()
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/source",
                "kaynak nedir?",
                "TR",
                date.today() - timedelta(days=800),
                True,
                "official",
            ),
        ),
        required_scope="TR",
        allowed_authorities=("official",),
        max_age_days=365,
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input="Kaynak nedir?",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "unverified"
    assert result.state.evidence_verified is False
    assert result.verdict == "ABSTAIN"


def test_untrusted_authority_blocks_verification():
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    package = evidence_package()
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/source",
                "kaynak nedir?",
                "TR",
                date.today(),
                True,
                "blog",
            ),
        ),
        required_scope="TR",
        allowed_authorities=("official",),
        max_age_days=365,
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input="Kaynak nedir?",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "unverified"
    assert result.state.evidence_verified is False
    assert result.verdict == "ABSTAIN"


def test_evidence_intent_recognizes_common_natural_language_variants():
    from anne.core.intent import IntentClassifier, IntentKind

    classifier = IntentClassifier()
    phrases = (
        "Bunun dayanağı ne?",
        "Bunu hangi kanıta göre söylüyorsun?",
        "Bu bilginin kaynağı nedir?",
        "What is the source for this?",
    )

    for phrase in phrases:
        frame = classifier.classify(phrase)
        assert frame.intent == IntentKind.EVIDENCE_REQUEST
        assert frame.requires_evidence is True


def test_evidence_audit_metadata_survives_context_map_rebuild():
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    package = EvidencePackage(
        mission_id="mission_audit",
        agent_id="agent_mitos",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim="655 W panel Türkiye'de 4.800 TL",
                source="https://example.com/panel",
                evidence_kind="WEB_SOURCE",
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
        ),
        required_scope="TR",
        allowed_authorities=("official",),
        max_age_days=365,
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input="655 W panel Türkiye'de 4.800 TL? Kaynağı nedir?",
        claim="655 W panel Türkiye'de 4.800 TL",
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.context_map["evidence_sources"] == ["https://example.com/panel"]
    assert result.state.context_map["evidence_reason"] == "All atomic claims passed independent source verification."


def test_cognitive_path_routes_evidence_to_independent_verifier(monkeypatch):
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord
    from anne.mythos.candidate import HypothesisCandidate
    from anne.mythos.engine import ExplorationMode

    claim = "655 W panel Türkiye'de 4.800 TL? Kaynağı nedir?"
    package = EvidencePackage(
        mission_id="mission_cognitive",
        agent_id="agent_mitos",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim=claim,
                source="https://example.com/panel",
                evidence_kind="WEB_SOURCE",
                provenance="MITOS:web_research",
            ),
        ),
    )
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/panel",
                claim,
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
    candidate = HypothesisCandidate(
        id="cand_verified",
        goal=claim,
        claim=claim,
        mode=ExplorationMode.HYPOTHESIS,
        probability=0.9,
        discovery_value=0.9,
        novelty=0.9,
        testability=1.0,
        harm_risk=0.0,
        reversibility=1.0,
        expected_benefit=0.9,
        test_cost=0.1,
        evidence_status="SIMULATION",
        score_origin="test_fixture",
    )
    monkeypatch.setattr(
        "anne.core.cognitive_orchestrator.generate_candidates",
        lambda *args, **kwargs: [candidate],
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run_cognitive(
        claim,
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "available"
    assert result.state.evidence_verified is True
    assert result.state.output["factual_status"] == "verified"
    assert result.state.context_map["evidence_sources"] == ["https://example.com/panel"]


def test_decision_result_preserves_verified_factual_status():
    from datetime import date
    from anne.core.source_verifier import SourceAwareVerifier, SourceRecord

    claim = "655 W panel Türkiye'de 4.800 TL"
    package = EvidencePackage(
        mission_id="mission_result",
        agent_id="agent_mitos",
        role=AgentRole.CUSTOM,
        findings=(
            EvidenceItem(
                claim=claim,
                source="https://example.com/panel",
                evidence_kind="WEB_SOURCE",
                provenance="MITOS:web_research",
            ),
        ),
    )
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                "https://example.com/panel",
                claim,
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

    result = DecisionLoop(memory=FractalMemory(":memory:")).run(
        raw_input=claim + "? Kaynağı nedir?",
        claim=claim,
        parties=[Consciousness(id="user")],
        evidence_packages=[package],
        verifier=verifier,
    )

    assert result.state is not None
    assert result.state.evidence_status == "available"
    assert result.output["factual_status"] == "verified"
    assert result.as_dict()["factual_status"] == "verified"


def test_mitos_candidate_evidence_status_never_promotes_to_factual_verification(monkeypatch):
    from anne.mythos.candidate import HypothesisCandidate
    from anne.mythos.engine import ExplorationMode

    claim = "655 W panel Türkiye'de 4.800 TL? Kaynağı nedir?"
    candidate = HypothesisCandidate(
        id="cand_claimed_verified",
        goal=claim,
        claim=claim,
        mode=ExplorationMode.HYPOTHESIS,
        probability=0.99,
        discovery_value=0.99,
        novelty=0.9,
        testability=1.0,
        harm_risk=0.0,
        reversibility=1.0,
        expected_benefit=0.9,
        test_cost=0.1,
        evidence_status="VERIFIED",
        score_origin="mitos_claim",
    )
    monkeypatch.setattr(
        "anne.core.cognitive_orchestrator.generate_candidates",
        lambda *args, **kwargs: [candidate],
    )

    result = DecisionLoop(memory=FractalMemory(":memory:")).run_cognitive(
        claim,
        parties=[Consciousness(id="user")],
    )

    assert result.state is not None
    assert result.state.context_map["candidate_evidence_status"] == "VERIFIED"
    assert result.state.evidence_status == "missing"
    assert result.state.evidence_verified is False
    assert result.state.context_map["evidence_gate"] == "blocked"
    assert result.state.output["factual_status"] == "unverified"
    assert result.status == "BOUNDED"
    assert result.stop_reason == "retry_budget_exhausted"
