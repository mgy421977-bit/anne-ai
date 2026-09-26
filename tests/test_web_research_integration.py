from anne.agent.runtime import AnneAgent
from anne.core.cognitive_runtime import CognitiveWorkspace
from anne.learning.evidence import EvidenceItem, EvidenceLedgerEntry, EvidenceStatus
from anne.learning.web_research import WebResearcher
from anne.safety.policy import ToolPolicy
from anne.core.verification import FactualStatus, ReferenceClaim, ReferenceVerifier


def test_web_research_is_allowlisted_as_read_only() -> None:
    decision = ToolPolicy().authorize("web_research", {"query": "BESS nedir?"})
    assert decision.allowed
    assert decision.side_effect is False
    assert decision.reversible is True
    assert decision.risk == 0.10
    assert decision.human_review_required is False


def test_web_research_output_is_provenance_bearing(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim=f"Evidence for {query}",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("test query")
    assert result["ok"] is True
    assert result["evidence_count"] == 1
    item = result["evidence"][0]
    assert item["provenance"] == "https://example.test/source"
    assert item["confidence"] == 0.8
    assert item["status"] == "unverified"
    assert result["independent_verification"] == "not_performed"


def test_web_research_is_exposed_to_model_tool_schema() -> None:
    names = {
        item["function"]["name"]
        for item in AnneAgent.TOOL_SCHEMAS
        if item.get("type") == "function"
    }
    assert "web_research" in names


def test_web_research_records_unverified_evidence_in_workspace(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim=f"Evidence for {query}",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    agent.workspace = CognitiveWorkspace(task="test query")
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("test query")

    assert result["evidence_count"] == 1
    assert len(agent.workspace.evidence_ledger) == 1
    entry = agent.workspace.evidence_ledger[0]
    assert isinstance(entry, EvidenceLedgerEntry)
    assert entry.status is EvidenceStatus.UNVERIFIED
    assert entry.provenance == "https://example.test/source"
    assert entry.claim == "Evidence for test query"


def test_evidence_ledger_rejects_missing_provenance() -> None:
    try:
        EvidenceLedgerEntry(
            claim="claim",
            source="source",
            provenance="",
            confidence=0.5,
        )
    except ValueError as exc:
        assert "provenance" in str(exc)
    else:
        raise AssertionError("missing provenance must fail closed")


def test_web_research_claim_can_be_verified_by_independent_verifier(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim="The capital of France is Paris.",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    agent.workspace = CognitiveWorkspace(task="test query")
    agent.response_verifier = ReferenceVerifier(
        (ReferenceClaim("The capital of France is Paris.", "atlas:1", True),)
    )
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("capital")

    assert result["evidence"][0]["status"] == "verified"
    assert result["evidence"][0]["verification_sources"] == ["atlas:1"]
    assert agent.workspace.evidence_ledger[0].status is EvidenceStatus.VERIFIED


def test_web_research_conflict_stays_conflicting(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim="The capital of France is Paris.",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    agent.workspace = CognitiveWorkspace(task="test query")
    agent.response_verifier = ReferenceVerifier(
        (
            ReferenceClaim("The capital of France is Paris.", "atlas:1", True),
            ReferenceClaim("The capital of France is Paris.", "atlas:2", False),
        )
    )
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("capital")

    assert result["evidence"][0]["status"] == FactualStatus.CONFLICTING.value
    assert agent.workspace.evidence_ledger[0].status is EvidenceStatus.CONFLICTING


def test_web_research_without_verifier_remains_unverified(monkeypatch) -> None:
    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim="A claim from the web.",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    agent.workspace = CognitiveWorkspace(task="test query")
    agent.response_verifier = None
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("claim")

    assert result["evidence"][0]["status"] == EvidenceStatus.UNVERIFIED.value
    assert agent.workspace.evidence_ledger[0].status is EvidenceStatus.UNVERIFIED


def test_research_evidence_alone_does_not_unlock_pipeline(tmp_path) -> None:
    from anne.core.decision_loop import DecisionLoop
    from anne.memory.fractal_memory import FractalMemory

    loop = DecisionLoop(memory=FractalMemory(tmp_path / "anne.db"))
    result = loop.run("The capital of France is Paris.")

    assert result.state is not None
    assert result.state.evidence_status != EvidenceStatus.AVAILABLE.value
    assert result.state.output.get("factual_status") != "verified"


def test_agent_exposes_end_to_end_evidence_trace(monkeypatch) -> None:
    from anne.core.verification import ReferenceClaim, ReferenceVerifier
    from anne.memory.local_memory import LocalMemory

    class FakeResearcher:
        def research(self, query):
            return [
                EvidenceItem(
                    source="test-source",
                    claim="The capital of France is Paris.",
                    kind="web",
                    provenance="https://example.test/source",
                    confidence=0.8,
                )
            ]

    agent = object.__new__(AnneAgent)
    agent.web_researcher = WebResearcher()
    agent.workspace = CognitiveWorkspace(task="capital")
    agent.response_verifier = ReferenceVerifier(
        (ReferenceClaim("The capital of France is Paris.", "independent:1", True),)
    )
    monkeypatch.setattr(agent.web_researcher, "research", FakeResearcher().research)

    result = agent._web_research("capital")

    assert result["evidence_count"] == 1
    assert agent.workspace.evidence_ledger[0].status is EvidenceStatus.VERIFIED

    trace = [
        {
            "claim": entry.claim,
            "source": entry.source,
            "provenance": entry.provenance,
            "status": entry.status.value,
        }
        for entry in agent.workspace.evidence_ledger
    ]
    assert trace == [
        {
            "claim": "The capital of France is Paris.",
            "source": "test-source",
            "provenance": "https://example.test/source",
            "status": "verified",
        }
    ]
