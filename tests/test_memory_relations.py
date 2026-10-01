from __future__ import annotations

from anne.memory.fractal_memory import FractalMemory


def test_explicit_memory_links_are_persistent(tmp_path) -> None:
    memory = FractalMemory(tmp_path / "anne.db")
    memory.save_memory_link("new_decision", "old_decision", "general", "2026-10-01T10:00:00")

    links = memory.get_memory_links()

    assert links
    assert links[0]["source_decision_id"] == "new_decision"
    assert links[0]["target_decision_id"] == "old_decision"
    assert links[0]["relation"] == "supersedes"
    assert links[0]["task_mode"] == "general"
