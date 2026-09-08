from pathlib import Path

from anne.translation.engine import TranslationEngine
from anne.translation.memory import TranslationMemory
from anne.translation.providers import TranslationCandidate


class StubProvider:
    def __init__(self, value: str):
        self.value = value
        self.calls = 0

    def translate(self, text, source_language, target_language, context=None):
        self.calls += 1
        return TranslationCandidate(
            direct=self.value,
            provider="stub",
            confidence=0.9,
            metadata={"context": context or {}},
        )


def test_unknown_is_learned_then_reused_offline(tmp_path: Path):
    memory = TranslationMemory(tmp_path / "memory.db")
    learner = StubProvider("Toplantıyı ertelememiz gerekiyor.")
    engine = TranslationEngine(
        memory=memory,
        local_provider=None,
        learning_provider=learner,
        learning_enabled=True,
    )

    first = engine.translate(
        "We need to push the meeting back.",
        context={"domain": "business"},
    )
    assert first.learned is True
    assert learner.calls == 1

    second = engine.translate("We need to push the meeting back.")
    assert second.source == "mitos_memory"
    assert second.direct == first.direct
    assert learner.calls == 1


def test_offline_mode_does_not_call_learning_provider(tmp_path: Path):
    memory = TranslationMemory(tmp_path / "memory.db")
    learner = StubProvider("öğrenilmemeliydi")
    engine = TranslationEngine(
        memory=memory,
        local_provider=None,
        learning_provider=learner,
        learning_enabled=False,
    )

    try:
        engine.translate("Unknown expression")
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing local provider should fail closed")

    assert learner.calls == 0
