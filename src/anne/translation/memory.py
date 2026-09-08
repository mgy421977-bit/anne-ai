from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryEntry:
    source_language: str
    target_language: str
    source_text: str
    direct_text: str
    semantic_text: str
    context: dict[str, Any]
    confidence: float
    learned_from: str


class TranslationMemory:
    """Persistent local bilingual memory for MITOS.

    Exact normalized matches are intentionally conservative: if ANNE has not
    learned an expression, the engine must not silently invent a memory hit.
    """

    def __init__(self, path: str | Path = "anne_translation_memory.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _key(text: str) -> str:
        return " ".join(text.casefold().strip().split())

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS translation_memory (
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    direct_text TEXT NOT NULL,
                    semantic_text TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    learned_from TEXT NOT NULL,
                    PRIMARY KEY (source_language, target_language, source_key)
                )"""
            )

    def lookup(self, source_language: str, target_language: str, text: str) -> MemoryEntry | None:
        key = self._key(text)
        with self._connect() as db:
            row = db.execute(
                """SELECT * FROM translation_memory
                   WHERE source_language=? AND target_language=? AND source_key=?""",
                (source_language, target_language, key),
            ).fetchone()
        if row is None:
            return None
        return MemoryEntry(
            source_language=row["source_language"],
            target_language=row["target_language"],
            source_text=row["source_text"],
            direct_text=row["direct_text"],
            semantic_text=row["semantic_text"],
            context=json.loads(row["context_json"]),
            confidence=float(row["confidence"]),
            learned_from=row["learned_from"],
        )

    def learn(self, entry: MemoryEntry) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO translation_memory
                   (source_language,target_language,source_key,source_text,
                    direct_text,semantic_text,context_json,confidence,learned_from)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(source_language,target_language,source_key)
                   DO UPDATE SET direct_text=excluded.direct_text,
                                 semantic_text=excluded.semantic_text,
                                 context_json=excluded.context_json,
                                 confidence=excluded.confidence,
                                 learned_from=excluded.learned_from""",
                (
                    entry.source_language,
                    entry.target_language,
                    self._key(entry.source_text),
                    entry.source_text,
                    entry.direct_text,
                    entry.semantic_text,
                    json.dumps(entry.context, ensure_ascii=False),
                    entry.confidence,
                    entry.learned_from,
                ),
            )
