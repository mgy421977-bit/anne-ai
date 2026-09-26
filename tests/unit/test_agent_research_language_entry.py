from anne.agent.runtime import AnneAgent
from anne.language_learning import LanguageLearningEngine
from anne.memory.local_memory import LocalMemory
from anne.research.web_search import WebSearchRequest, WebSearchResult


class FakeModel:
    def ask(self, prompt: str, system_instruction: str = "") -> str:
        return "<RESPONSE>unused</RESPONSE><LEARNING>No new durable learning.</LEARNING><CONFIDENCE>0.5</CONFIDENCE>"


class FakeSearchProvider:
    def search(self, request: WebSearchRequest):
        return (
            WebSearchResult(
                title="Research source",
                url="https://example.org/source",
                snippet="candidate evidence",
                source_domain="example.org",
            ),
        )


def test_agent_entry_point_starts_research_before_guarded_reasoning(tmp_path):
    memory = LocalMemory(tmp_path / "memory")
    agent = AnneAgent(
        FakeModel(),
        memory,
        research_provider=FakeSearchProvider(),
    )
    result = agent.run("Güncel BESS mevzuatını araştır")
    assert result.cognitive_review.get("research_mission_id") is not None or result.response
    assert result.verification["status"] == "unverified"


def test_agent_entry_point_requires_language_authorization(tmp_path):
    memory = LocalMemory(tmp_path / "memory")
    agent = AnneAgent(FakeModel(), memory)
    result = agent.run("ANNE Türkçe öğren")
    assert result.verification["response_withheld"] is True
    assert result.cognitive_review["authorization_required"] is True


def test_authorized_language_learning_can_start_research(tmp_path):
    memory = LocalMemory(tmp_path / "memory")
    languages = LanguageLearningEngine()
    languages.authorize("English", "en", granted_by="human")
    agent = AnneAgent(
        FakeModel(),
        memory,
        language_engine=languages,
        research_provider=FakeSearchProvider(),
    )
    result = agent.run("ANNE İngilizce öğren")
    assert result.cognitive_review["mode"] == "LANGUAGE_LEARNING"
    assert result.cognitive_review["mission_id"]


def test_agent_entry_point_can_force_research_for_client_requests(tmp_path):
    memory = LocalMemory(tmp_path / "memory")
    agent = AnneAgent(
        FakeModel(),
        memory,
        research_provider=FakeSearchProvider(),
    )
    result = agent.run("What is the current status?", force_research=True)
    assert result.verification["status"] == "unverified"


def test_agent_entry_point_exposes_explicit_language_authorization(tmp_path):
    memory = LocalMemory(tmp_path / "memory")
    agent = AnneAgent(FakeModel(), memory)
    profile = agent.authorize_language_learning(
        "Deutsch", "de", granted_by="human"
    )
    assert profile.authorized is True
    assert profile.code == "de"
