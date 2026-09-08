"""Persistent local workspace for the ANNE live meeting translator.

User meeting data never belongs in the Git repository.  This module creates a
stable, configurable directory tree on the local Windows disk and provides
small helpers for append-only JSONL records and SQLite-backed local memory.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(os.environ.get("ANNE_DATA_DIR", Path.home() / "ANNE" / "data"))


@dataclass(frozen=True)
class MeetingWorkspace:
    """Paths belonging to one meeting session."""

    root: Path
    meeting_id: str

    @property
    def recording_dir(self) -> Path:
        return self.root / "recordings" / "meetings" / self.meeting_id

    @property
    def transcript_file(self) -> Path:
        return self.root / "transcripts" / f"{self.meeting_id}.jsonl"

    @property
    def direct_translation_file(self) -> Path:
        return self.root / "translations" / self.meeting_id / "direct_tr.jsonl"

    @property
    def semantic_translation_file(self) -> Path:
        return self.root / "translations" / self.meeting_id / "semantic_tr.jsonl"

    @property
    def report_file(self) -> Path:
        return self.root / "reports" / f"{self.meeting_id}.json"

    @property
    def audio_file(self) -> Path:
        return self.recording_dir / "audio.wav"

    def create(self) -> "MeetingWorkspace":
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file.parent.mkdir(parents=True, exist_ok=True)
        self.direct_translation_file.parent.mkdir(parents=True, exist_ok=True)
        self.semantic_translation_file.parent.mkdir(parents=True, exist_ok=True)
        self.report_file.parent.mkdir(parents=True, exist_ok=True)
        return self

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(record)
        payload.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append_transcript(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.transcript_file, record)

    def append_direct_translation(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.direct_translation_file, record)

    def append_semantic_translation(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.semantic_translation_file, record)

    def write_report(self, report: dict[str, Any]) -> None:
        self.report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )


class ANNEWorkspace:
    """Owns ANNE's local data, models and persistent MITOS memory."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.models_dir = self.root / "models"
        self.memory_dir = self.root / "memory"
        self.logs_dir = self.root / "logs"
        self.config_dir = self.root / "config"
        self.db_path = self.memory_dir / "mitos.sqlite3"

    def initialize(self) -> None:
        for directory in (
            self.root,
            self.root / "recordings" / "meetings",
            self.root / "transcripts",
            self.root / "translations",
            self.root / "reports",
            self.models_dir,
            self.memory_dir,
            self.logs_dir,
            self.config_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS learned_terms (
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    provider TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(source, source_language, target_language)
                )"""
            )
            db.commit()

    def meeting(self, meeting_id: str | None = None) -> MeetingWorkspace:
        if meeting_id is None:
            meeting_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return MeetingWorkspace(self.root, meeting_id).create()

    def disk_status(self, minimum_free_gb: float = 5.0) -> dict[str, float | bool]:
        usage = shutil.disk_usage(self.root)
        free_gb = usage.free / (1024**3)
        return {
            "free_gb": round(free_gb, 2),
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "safe": free_gb >= minimum_free_gb,
        }

    def connect_memory(self) -> sqlite3.Connection:
        self.initialize()
        return sqlite3.connect(self.db_path)
