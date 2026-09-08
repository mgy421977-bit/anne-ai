from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TranslationMemory:
    """Persistent, local MITOS memory for learned translation mappings."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] = self._load()

    @staticmethod
    def _key(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def lookup(self, source: str) -> dict[str, Any] | None:
        return self._data.get(self._key(source))

    def remember(
        self,
        source: str,
        direct: str,
        semantic: str,
        *,
        context: dict[str, Any] | None = None,
        provider: str = "local",
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        record = {
            "source": source,
            "direct": direct,
            "semantic": semantic,
            "context": context or {},
            "provider": provider,
            "confidence": max(0.0, min(1.0, confidence)),
            "offline_ready": True,
        }
        self._data[self._key(source)] = record
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record
