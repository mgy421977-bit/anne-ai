"""V1 freeze: demo identity, memory isolation, cognitive path wiring, honesty helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from anne.core.users import resolve_user
from anne.memory.local_memory import LocalMemory


def test_donerci_mistik_maps_to_mustafa() -> None:
    idn = resolve_user("Dönerci Mıstık")
    assert idn.user_id == "mustafa"
    assert idn.display_name == "Mustafa Bey"
    assert "Mustafa Bey" in idn.greeting
    assert idn.is_demo is True


def test_gugu_baba_maps_to_gurhan() -> None:
    idn = resolve_user("Gügü Baba")
    assert idn.user_id == "gurhan"
    assert idn.display_name == "Gürhan Bey"
    assert "Gürhan Bey" in idn.greeting


def test_user_memory_isolation(tmp_path: Path) -> None:
    db = tmp_path / "m.sqlite3"
    mem = LocalMemory(db)
    mem.save("X nedir?", "mustafa cevabi", "l", 0.8, user_id="mustafa")
    mem.save("X nedir?", "gurhan cevabi", "l", 0.8, user_id="gurhan")
    assert mem.find_previous_answer("X nedir?", user_id="mustafa")["response"] == "mustafa cevabi"
    assert mem.find_previous_answer("X nedir?", user_id="gurhan")["response"] == "gurhan cevabi"
    prev_m = mem.find_previous_answer("X nedir?", user_id="mustafa")
    prev_g = mem.find_previous_answer("X nedir?", user_id="gurhan")
    assert prev_m is not None and prev_g is not None
    assert prev_m["response"] != prev_g["response"]


def test_experience_isolation(tmp_path: Path) -> None:
    mem = LocalMemory(tmp_path / "e.sqlite3")

    class E:
        actor = "Dönerci Mıstık"
        question = "q"
        approach = ["research_used"]
        evaluation_criteria = []
        objections = []
        outcome = "UPDATED"

    mem.save_experience(E(), user_id="mustafa")
    assert len(mem.recent_experiences(user_id="mustafa")) == 1
    assert len(mem.recent_experiences(user_id="gurhan")) == 0


def test_share_experience_default_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANNE_SHARE_EXPERIENCE", raising=False)
    mem = LocalMemory(tmp_path / "s.sqlite3")

    class E:
        actor = "x"
        question = "secret question"
        approach = []
        evaluation_criteria = []
        objections = []
        outcome = "UNCHANGED"

    mem.save_experience(E(), user_id="mustafa")
    outbox = tmp_path / "experiences" / "anonymous_outbox.jsonl"
    assert not outbox.exists()


def test_anonymize_strips_content() -> None:
    from anne.github.sync import anonymize_experience

    payload = anonymize_experience(
        {
            "comparison_status": "UPDATED",
            "research_used": True,
            "question": "SHOULD_NOT_APPEAR",
            "answer": "SHOULD_NOT_APPEAR",
            "actor": "Mustafa",
        },
        version="v1",
    )
    blob = str(payload)
    assert "SHOULD_NOT_APPEAR" not in blob
    assert "Mustafa" not in blob
    assert payload["comparison_status"] == "UPDATED"


def test_github_sync_skips_non_main_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from anne.github import sync as gsync

    (tmp_path / ".git").mkdir()

    class R:
        def __init__(self, code=0, out="", err=""):
            self.returncode = code
            self.stdout = out
            self.stderr = err

    def fake_run(root, *args, timeout=30):
        if args[:2] == ("remote", "get-url"):
            return R(0, "https://github.com/mgy421977-bit/anne-ai.git\n")
        if args[0] == "fetch":
            return R(0, "")
        if args[:2] == ("branch", "--show-current"):
            return R(0, "feature/laptop-web-tinker\n")
        if args[0] == "pull":
            raise AssertionError("pull must not run on feature branch")
        return R(0, "")

    monkeypatch.setattr(gsync, "_run_git", fake_run)
    result = gsync.ensure_repository_connection(tmp_path)
    assert result["status"] == "update_available_not_applied"
    assert result.get("current_branch") == "feature/laptop-web-tinker"


def test_filter_model_attribution() -> None:
    from anne.core.conversation import _filter_model_attribution

    text = "ChatGPT'ye göre cevap budur. Gemini dedi ki farklı."
    out = _filter_model_attribution(text)
    assert "ChatGPT" not in out or "Araştırma" in out or out != text
