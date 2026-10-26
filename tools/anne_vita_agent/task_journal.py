"""Local audit journal and report model for the bounded ANNE agent.

The journal stores task metadata and outcomes, not raw email bodies or credentials.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_SECRET_KEY = re.compile(r"(password|secret|token|api[_-]?key|authorization|credential)", re.I)
_SENSITIVE_CONTENT_KEYS = {"body", "raw_body", "email_body", "attachment_content"}


def _safe_value(value: Any, *, key: str = "") -> Any:
    """Redact credentials and avoid journaling raw email/document contents."""
    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if key.lower() in _SENSITIVE_CONTENT_KEYS:
        return "[OMITTED]"
    if isinstance(value, dict):
        return {str(k): _safe_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@dataclass(frozen=True)
class TaskReport:
    """Stable, user-readable report structure; it does not imply results are verified."""

    task_id: str
    status: str
    summary: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    calculation: dict[str, Any] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return _safe_value(asdict(self))


class TaskJournal:
    """Append-only JSONL journal scoped to the configured local workspace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.path.is_file():
            raise ValueError("journal path must be a file")

    def record(self, event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event must be a non-empty string")
        if details is not None and not isinstance(details, dict):
            raise ValueError("details must be a JSON object")
        entry = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.strip(),
            "details": _safe_value(details or {}),
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
        return entry

    def read_entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid journal JSON on line {line_number}") from exc
                if not isinstance(entry, dict):
                    raise ValueError(f"journal line {line_number} must be an object")
                entries.append(entry)
        return entries
