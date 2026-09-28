"""Tests for provider-free native conversation."""

from anne.core.cognitive_state import CognitiveState
from anne.core.pipeline import AnnePipeline
from anne.memory.fractal_memory import FractalMemory
from anne.core.conversation import NativeConversation


def test_native_conversation_greeting_does_not_need_model():
    conversation = NativeConversation(memory=FractalMemory(":memory:"))

    turn = conversation.respond("Merhaba ANNE")

    assert isinstance(turn.state, CognitiveState)
    assert turn.state.intent == "greeting"
    assert "Ben ANNE" in turn.response
    assert len(conversation.turns) == 1


def test_native_conversation_question_is_bounded_and_does_not_invent_answer():
    conversation = NativeConversation(memory=FractalMemory(":memory:"))

    turn = conversation.respond("Neden böyle çalışıyorsun?")

    assert turn.state.intent == "question"
    assert "uydurmak yerine" in turn.response


def test_native_conversation_keeps_turn_history_without_external_provider():
    memory = FractalMemory(":memory:")
    conversation = NativeConversation(memory=memory, pipeline=AnnePipeline(memory))

    first = conversation.respond("Merhaba")
    second = conversation.respond("Bunu bir soru olarak düşün")

    assert first.user_input == "Merhaba"
    assert second.user_input == "Bunu bir soru olarak düşün"
    assert len(conversation.turns) == 2
    assert all(turn.state.raw_input for turn in conversation.turns)
