"""Media context contracts for ANNE's local cognitive environment.

This layer does not decode or redistribute media.  It represents a media
session supplied by the user or an authorized local player so that a scene,
timestamp and user question can become explicit cognitive context.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaContext:
    media_path: str
    title: str
    position_seconds: float = 0.0
    scene_label: str | None = None
    user_note: str | None = None

    def __post_init__(self) -> None:
        if self.position_seconds < 0:
            raise ValueError("position_seconds must be non-negative")

    @property
    def position_label(self) -> str:
        total = int(self.position_seconds)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        position_seconds: float = 0.0,
        scene_label: str | None = None,
        user_note: str | None = None,
    ) -> "MediaContext":
        resolved = Path(path).expanduser()
        return cls(
            media_path=str(resolved),
            title=resolved.stem or resolved.name,
            position_seconds=position_seconds,
            scene_label=scene_label,
            user_note=user_note,
        )

    def discussion_prompt(self, question: str) -> str:
        details = [
            f"Media: {self.title}",
            f"Local path: {self.media_path}",
            f"Position: {self.position_label}",
        ]
        if self.scene_label:
            details.append(f"Scene: {self.scene_label}")
        if self.user_note:
            details.append(f"User scene note: {self.user_note}")
        details.append(f"Question: {question.strip()}")
        return "\n".join(details)


__all__ = ["MediaContext"]
