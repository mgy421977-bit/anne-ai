"""Safe local-media launcher abstraction for ANNE.

ANNE does not download, bypass DRM, or install media software.  It can launch
an existing local media file with an already-installed player, leaving media
decoding to the operating system/player.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


class LocalMediaLauncher:
    """Open a user-selected local media file with an existing player."""

    def __init__(self, *, player_command: str | None = None) -> None:
        self.player_command = player_command

    def available_player(self) -> str | None:
        if self.player_command:
            return self.player_command if shutil.which(self.player_command) else None
        for candidate in ("mpv", "vlc", "ffplay"):
            if shutil.which(candidate):
                return candidate
        return None

    def open(self, path: str | Path) -> str:
        media = Path(path).expanduser()
        if not media.is_file():
            raise FileNotFoundError(media)

        player = self.available_player()
        if player:
            subprocess.Popen(
                [player, str(media)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return player

        system = platform.system()
        if system == "Windows":
            os.startfile(str(media))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(media)])
        elif shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(media)])
        else:
            raise RuntimeError("no local media player or OS opener is available")
        return "os-default"

    def can_open(self, path: str | Path) -> bool:
        try:
            return Path(path).expanduser().is_file()
        except OSError:
            return False


__all__ = ["LocalMediaLauncher"]
