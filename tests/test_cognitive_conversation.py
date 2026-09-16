from anne.core.conversation import CognitiveConversation


class FakeLanguage:
    def __init__(self) -> None:
        self.calls = []

    def express(self, content: str, *, language: str = "tr") -> str:
        self.calls.append(content)
        return "ANNE: " + content.split("Soru: ", 1)[1].split("\n", 1)[0]


class FakeResearch:
    def __init__(self) -> None:
        self.calls = []

    def research(self, question: str):
        self.calls.append(question)
        return {"ok": True, "sources": ["current"]}


class FakeConsultation:
    def __init__(self) -> None:
        self.calls = []

    def ask(self, question: str, context):
        self.calls.append((question, context))
        return {"ok": True, "answer": "external explanation"}


def test_anne_controls_research_and_language_only_expresses():
    language = FakeLanguage()
    research = FakeResearch()
    consultation = FakeConsultation()
    conversation = CognitiveConversation(
        language=language,
        research=research,
        consultation=consultation,
    )

    result = conversation.handle("GÖKHAN", "Aynı soru tekrar geldi mi?", known_context="old answer")

    assert research.calls == ["Aynı soru tekrar geldi mi?"]
    assert consultation.calls == []
    assert len(language.calls) == 1
    assert result.answer.startswith("ANNE:")
    assert result.experience is not None
    assert result.experience.actor == "GÖKHAN"


def test_consultation_is_an_anne_decision_not_a_model_tool_call():
    language = FakeLanguage()
    consultation = FakeConsultation()
    conversation = CognitiveConversation(language=language, consultation=consultation)

    result = conversation.handle("GÖKHAN", "Bunu bilmiyorum.")

    assert consultation.calls
    assert result.current_evidence == 1
    assert "CHATGPT" not in language.calls[0]
