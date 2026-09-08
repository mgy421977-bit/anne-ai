from pathlib import Path

from anne.translation.engine import TranslationEngine
from anne.translation.memory import TranslationMemory


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def translate(self, text: str, source: str = "en", target: str = "tr") -> str:
        self.calls += 1
        return f"TR:{text}"


def test_unknown_expression_learns_then_becomes_offline(tmp_path: Path):
    provider = FakeProvider()
    memory = TranslationMemory(tmp_path / "memory.json")
    engine = TranslationEngine(memory, provider)

    first = engine.translate("We need to move the deadline.", speaker="Michael")
    assert first.source_mode == "learning"
    assert first.learned is True
    assert provider.calls == 1

    second = engine.translate("We need to move the deadline.", speaker="Michael")
    assert second.source_mode == "memory"
    assert second.learned is False
    assert provider.calls == 1
    assert second.direct == first.direct


def test_unknown_expression_can_be_blocked_offline(tmp_path: Path):
    memory = TranslationMemory(tmp_path / "memory.json")
    engine = TranslationEngine(memory, None, learning_enabled=False)

    try:
        engine.translate("A new expression")
    except LookupError:
        pass
    else:
        raise AssertionError("Unknown expression must not silently invent a translation")
