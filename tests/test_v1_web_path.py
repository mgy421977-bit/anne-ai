"""End-to-end style tests for V1 web cognitive path (no live network)."""

from __future__ import annotations

from pathlib import Path

from anne.core.conversation import CognitiveConversation
from anne.memory.local_memory import LocalMemory


class FakeLang:
    def express(self, content: str, *, language: str = "tr") -> str:
        return "ANNE: " + content[:60]


class FakeResearch:
    def __init__(self, text: str = "kanıt alfa beta") -> None:
        self.text = text
        self.calls: list[str] = []

    def research(self, question: str):
        self.calls.append(question)
        return {"ok": True, "data": self.text}


def test_web_path_structured_memory_to_conversation(tmp_path: Path) -> None:
    mem = LocalMemory(tmp_path / "w.db")
    research = FakeResearch("X tanımı net ve sabittir")
    conv = CognitiveConversation(language=FakeLang(), research=research)

    r1 = conv.handle("GÖKHAN", "X nedir?", previous_answer=None, recent_experiences=[])
    assert r1.audit is not None
    assert r1.audit.research_required is True
    mem.save("X nedir?", r1.answer, r1.learned, r1.audit.confidence)
    if r1.experience:
        mem.save_experience(r1.experience)

    prev = mem.find_previous_answer("X nedir?")
    assert prev is not None
    exps = mem.recent_experiences(limit=3)
    assert len(exps) >= 1

    r2 = conv.handle(
        "GÖKHAN",
        "X nedir?",
        previous_answer=prev,
        recent_experiences=exps,
    )
    assert r2.audit is not None
    assert r2.audit.previous_knowledge_found is True
