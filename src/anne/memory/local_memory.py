"""Local SQLite-backed memory for ANNE facts and experience patterns.

Factual interactions and problem-solving experiences are kept in separate
tables so human preferences are never treated as world facts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anne.memory.persistence import connect_memory


class LocalMemory:
    """Durable memory backend for interactions and observed problem-solving patterns."""

    def __init__(self, db_path: str | Path = "anne_web.db") -> None:
        self.conn = connect_memory(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS interactions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, "
            "user_input TEXT, response TEXT, learning TEXT, confidence REAL)"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS experiences ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, actor TEXT, "
            "question TEXT, approach TEXT, criteria TEXT, objections TEXT, outcome TEXT)"
        )
        self.conn.commit()

    def context(self, limit: int = 8) -> str:
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

    def find_previous_answer(self, question: str) -> dict[str, Any] | None:
        """Return the most recent structured factual answer for an exact question match.

        V1 uses deterministic exact match only. Semantic / vector search is deferred.
        """
        normalized = question.strip()
        if not normalized:
            return None
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

    def save(self, user_input: str, response: str, learning: str, confidence: float = 0.5) -> str:
        timestamp = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO interactions(timestamp, user_input, response, learning, confidence) "
            "VALUES (?, ?, ?, ?, ?)",
            (timestamp, user_input, response, learning, max(0.0, min(1.0, confidence))),
        )
        self.conn.commit()
        row_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return f"local:interactions/{row_id}"

    def save_experience(self, experience: object) -> str:
        """Persist an observed problem-solving pattern separately from factual memory."""
        timestamp = datetime.now(UTC).isoformat()
        self.conn.execute(
            "INSERT INTO experiences(timestamp, actor, question, approach, criteria, objections, outcome) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                str(getattr(experience, "actor", "unknown")),
                str(getattr(experience, "question", "")),
                json.dumps(getattr(experience, "approach", []), ensure_ascii=False),
                json.dumps(getattr(experience, "evaluation_criteria", []), ensure_ascii=False),
                json.dumps(getattr(experience, "objections", []), ensure_ascii=False),
                str(getattr(experience, "outcome", "")),
            ),
        )
        self.conn.commit()
        row_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return f"local:experiences/{row_id}"

    def recent_experiences(self, limit: int = 8) -> list[dict[str, object]]:
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
