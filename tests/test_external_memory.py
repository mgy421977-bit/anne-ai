"""External durable memory root tests (storage only)."""

from __future__ import annotations

from pathlib import Path

from anne.memory.local_memory import LocalMemory
from anne.memory.paths import (
    DB_NAME,
    SUBDIRS,
    backup_sqlite,
    discover_existing_anne_roots,
    ensure_layout,
    resolve_memory_location,
)


def test_ensure_layout_creates_subdirs(tmp_path: Path) -> None:
    root = tmp_path / "ANNE"
    ensure_layout(root)
    for name in SUBDIRS:
        assert (root / name).is_dir()
    assert (root / ".anne_memory_root").is_file()


def test_resolve_explicit_durable(tmp_path: Path) -> None:
    root = tmp_path / "E_ANNE"
    loc = resolve_memory_location(explicit=root)
    assert loc.durable is True
    assert loc.db_path == root / "memory" / DB_NAME
    assert loc.db_path.parent.is_dir()


def test_sqlite_on_external_path_persists(tmp_path: Path) -> None:
    root = tmp_path / "ANNE"
    loc = resolve_memory_location(explicit=root)
    mem = LocalMemory(loc.db_path)
    mem.save("X nedir?", "X test cevabi", "learning=test", 0.7)
    mem.save_experience(
        type("E", (), {"actor": "U", "question": "X nedir?", "approach": ["research_used"]})()
    )
    mem2 = LocalMemory(loc.db_path)
    prev = mem2.find_previous_answer("X nedir?")
    assert prev is not None
    assert prev["response"] == "X test cevabi"
    assert len(mem2.recent_experiences()) == 1


def test_existing_memory_detection(tmp_path: Path) -> None:
    root = tmp_path / "ANNE"
    ensure_layout(root)
    found = discover_existing_anne_roots(extra=[root])
    assert any(p.resolve() == root.resolve() for p in found)


def test_missing_configured_root_message(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANNE_MEMORY_ROOT", raising=False)
    monkeypatch.delenv("ANNE_WEB_DB", raising=False)
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    loc = resolve_memory_location(project_fallback=proj / "anne_data")
    assert loc.durable is False
    assert loc.source == "temporary"
    assert "Kalıcı ANNE Memory bulunamadı" in loc.message


def test_backup_sqlite(tmp_path: Path) -> None:
    root = tmp_path / "ANNE"
    loc = resolve_memory_location(explicit=root)
    mem = LocalMemory(loc.db_path)
    mem.save("q", "a", "l", 0.5)
    backup = backup_sqlite(loc.db_path)
    assert backup is not None
    assert Path(backup).is_file()


def test_integrity_check(tmp_path: Path) -> None:
    loc = resolve_memory_location(explicit=tmp_path / "ANNE")
    mem = LocalMemory(loc.db_path)
    ok, msg = mem.integrity_check()
    assert ok is True
    assert msg.lower() == "ok"


def test_api_key_not_in_schema(tmp_path: Path) -> None:
    loc = resolve_memory_location(explicit=tmp_path / "ANNE")
    mem = LocalMemory(loc.db_path)
    cols = []
    for table in ("interactions", "experiences"):
        for row in mem.conn.execute(f"PRAGMA table_info({table})").fetchall():
            cols.append(row[1].lower())
    forbidden = {"api_key", "secret", "token", "password", "openai_key", "xai_key"}
    assert forbidden.isdisjoint(set(cols))
