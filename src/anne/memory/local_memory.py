"""Local SQLite-backed memory for ANNE facts and experience patterns.

Factual interactions and problem-solving experiences are kept in separate
tables so human preferences are never treated as world facts.

This module is storage only. It does not decide research, comparison, or
revision — those remain in CognitiveConversation. API keys must never be
stored in this database.

V1 user isolation: optional user_id scopes reads/writes so demo users
(Mustafa / Gürhan) never share memory.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anne.github.sync import queue_anonymized_experience
from anne.memory.paths import backup_sqlite
from anne.memory.persistence import connect_memory


class LocalMemory:
    """Durable memory backend for interactions and observed problem-solving patterns."""

    def __init__(self, db_path: str | Path = "anne_web.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = connect_memory(self.db_path)
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error:
            pass
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS interactions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, "
            "user_input TEXT, response TEXT, learning TEXT, confidence REAL, "
            "user_id TEXT DEFAULT '')"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS experiences ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, actor TEXT, "
            "question TEXT, approach TEXT, criteria TEXT, objections TEXT, outcome TEXT, "
            "user_id TEXT DEFAULT '')"
        )
        self._ensure_user_id_columns()
        self.conn.commit()

    def _ensure_user_id_columns(self) -> None:
        for table in ("interactions", "experiences"):
            cols = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "user_id" not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT DEFAULT ''")

    def integrity_check(self) -> tuple[bool, str]:
        try:
            row = self.conn.execute("PRAGMA integrity_check").fetchone()
            msg = str(row[0]) if row else "unknown"
            return msg.lower() == "ok", msg
        except sqlite3.Error as exc:
            return False, str(exc)

    def backup(self) -> str | None:
        path = backup_sqlite(self.db_path)
        return str(path) if path else None

    def interaction_count(self, user_id: str = "") -> int:
        if user_id:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM interactions WHERE user_id = ?", (user_id,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM interactions").fetchone()
        return int(row[0]) if row else 0

    def context(self, limit: int = 8, *, user_id: str = "") -> str:
        if user_id:
            rows = self.conn.execute(
                "SELECT timestamp, user_input, learning, response FROM interactions "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT timestamp, user_input, learning, response FROM interactions "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        if not rows:
            return "No local memories have been recorded yet."
        return "\n\n---\n\n".join(
            f"[{row[0]}] USER: {row[1]}\nLEARNING: {row[2]}\nRESPONSE: {row[3]}"
            for row in rows
        )

    def find_previous_answer(
        self, question: str, *, user_id: str = ""
    ) -> dict[str, Any] | None:
        normalized = question.strip()
        if not normalized:
            return None
        if user_id:
            row = self.conn.execute(
                "SELECT timestamp, user_input, response, learning, confidence "
                "FROM interactions WHERE user_input = ? AND user_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (normalized, user_id),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT timestamp, user_input, response, learning, confidence "
                "FROM interactions WHERE user_input = ? ORDER BY id DESC LIMIT 1",
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        return {
            "timestamp": row[0],
            "question": row[1],
            "response": row[2],
            "learning": row[3],
            "confidence": float(row[4]) if row[4] is not None else 0.5,
        }

    def save(
        self,
        user_input: str,
        response: str,
        learning: str,
        confidence: float = 0.5,
        *,
        user_id: str = "",
    ) -> str:
        timestamp = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO interactions(timestamp, user_input, response, learning, confidence, user_id) "  # noqa: E501
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                user_input,
                response,
                learning,
                max(0.0, min(1.0, confidence)),
                user_id or "",
            ),
        )
        self.conn.commit()
        row_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return f"local:interactions/{row_id}"

    def save_experience(self, experience: object, *, user_id: str = "") -> str:
        timestamp = datetime.now(UTC).isoformat()
        actor = str(getattr(experience, "actor", "unknown"))
        self.conn.execute(
            "INSERT INTO experiences(timestamp, actor, question, approach, criteria, objections, outcome, user_id) "  # noqa: E501
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                actor,
                str(getattr(experience, "question", "")),
                json.dumps(getattr(experience, "approach", []), ensure_ascii=False),
                json.dumps(getattr(experience, "evaluation_criteria", []), ensure_ascii=False),
                json.dumps(getattr(experience, "objections", []), ensure_ascii=False),
                str(getattr(experience, "outcome", "")),
                user_id or "",
            ),
        )
        self.conn.commit()
        row_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if (os.getenv("ANNE_SHARE_EXPERIENCE") or "").strip().lower() in {"1", "true", "yes"}:
            try:
                root = (
                    self.db_path.parent.parent
                    if self.db_path.parent.name == "memory"
                    else Path.cwd()
                )
                queue_anonymized_experience(
                    root,
                    {
                        "comparison_status": getattr(experience, "outcome", "UNKNOWN"),
                        "research_used": "research_used"
                        in list(getattr(experience, "approach", []) or []),
                        "previous_answer_used": "previous_answer_used"
                        in list(getattr(experience, "approach", []) or []),
                        "previous_answer_changed": "previous_answer_changed"
                        in list(getattr(experience, "approach", []) or []),
                        "uncertainty_detected": False,
                        "anne_evaluation_formed": True,
                        "confidence": None,
                    },
                    version="v1",
                )
            except OSError:
                pass
        return f"local:experiences/{row_id}"

    def recent_experiences(
        self, limit: int = 8, *, user_id: str = ""
    ) -> list[dict[str, object]]:
        if user_id:
            rows = self.conn.execute(
                "SELECT timestamp, actor, question, approach, criteria, objections, outcome "
                "FROM experiences WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT timestamp, actor, question, approach, criteria, objections, outcome "
                "FROM experiences ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "timestamp": row[0],
                "actor": row[1],
                "question": row[2],
                "approach": json.loads(row[3]),
                "criteria": json.loads(row[4]),
                "objections": json.loads(row[5]),
                "outcome": row[6],
            }
            for row in rows
        ]


__all__ = ["LocalMemory"]
