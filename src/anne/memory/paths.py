"""External / local ANNE memory root layout (storage only, not cognitive authority).

ANNE may keep durable state on a user-selected drive, e.g. E:\\ANNE\\:

  memory/       SQLite factual + experience DB
  experiences/  optional export/debug copies
  knowledge/    reserved for V1 factual exports
  research/     reserved for evidence snapshots
  audit/        cognitive audit exports (optional)
  conversations/
  backups/      SQLite file copies
  logs/

API keys and secrets must never be written into the memory database.
"""

from __future__ import annotations

import os
import shutil
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

SUBDIRS: tuple[str, ...] = (
    "memory",
    "experiences",
    "knowledge",
    "research",
    "audit",
    "conversations",
    "backups",
    "logs",
)

DB_NAME = "anne_memory.sqlite3"
MARKER_NAME = ".anne_memory_root"
CONFIG_KEY = "ANNE_MEMORY_ROOT"


@dataclass(frozen=True)
class MemoryLocation:
    """Resolved durable (or temporary) memory root."""

    root: Path
    db_path: Path
    exists_prior: bool
    durable: bool
    source: str  # configured | detected | temporary | explicit
    message: str = ""


def _is_anne_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / MARKER_NAME).is_file():
        return True
    mem = path / "memory"
    if mem.is_dir() and any(mem.glob("*.sqlite3")):
        return True
    return False


def candidate_drive_roots() -> list[Path]:
    found: list[Path] = []
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:/")
        try:
            if root.exists():
                found.append(root)
        except OSError:
            continue
    for p in (Path("/mnt"), Path("/media"), Path("/Volumes")):
        try:
            if p.is_dir():
                for child in sorted(p.iterdir()):
                    if child.is_dir():
                        found.append(child)
        except OSError:
            continue
    return found


def discover_existing_anne_roots(extra: Iterable[Path] | None = None) -> list[Path]:
    hits: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen:
            return
        if _is_anne_root(p):
            seen.add(key)
            hits.append(p)

    env = (os.getenv(CONFIG_KEY) or "").strip()
    if env:
        add(Path(env))

    cwd = Path.cwd()
    add(cwd / "ANNE")
    add(cwd / "anne_data")

    for drive in candidate_drive_roots():
        add(drive / "ANNE")
        try:
            for child in drive.iterdir():
                if child.is_dir() and child.name.upper() == "ANNE":
                    add(child)
        except OSError:
            continue

    if extra:
        for p in extra:
            add(Path(p))

    return hits


def ensure_layout(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    marker = root / MARKER_NAME
    if not marker.exists():
        marker.write_text(
            "ANNE V1 memory root\n"
            "This directory stores factual memory and experiences only.\n"
            "It does not store API keys.\n",
            encoding="utf-8",
        )
    return root


def db_path_for(root: Path) -> Path:
    return root / "memory" / DB_NAME


def resolve_memory_location(
    *,
    explicit: str | Path | None = None,
    allow_temporary: bool = True,
    project_fallback: Path | None = None,
) -> MemoryLocation:
    if explicit is not None and str(explicit).strip():
        root = Path(str(explicit).strip())
        prior = _is_anne_root(root)
        ensure_layout(root)
        return MemoryLocation(
            root=root,
            db_path=db_path_for(root),
            exists_prior=prior,
            durable=True,
            source="explicit",
            message="Using explicit ANNE memory root",
        )

    env = (os.getenv(CONFIG_KEY) or "").strip()
    if env:
        root = Path(env)
        prior = _is_anne_root(root)
        try:
            ensure_layout(root)
            return MemoryLocation(
                root=root,
                db_path=db_path_for(root),
                exists_prior=prior,
                durable=True,
                source="configured",
                message=f"Configured memory root: {root}",
            )
        except OSError as exc:
            return MemoryLocation(
                root=root,
                db_path=db_path_for(root),
                exists_prior=False,
                durable=False,
                source="configured",
                message=f"Kalıcı ANNE Memory bulunamadı veya erişilemiyor: {exc}",
            )

    existing = discover_existing_anne_roots()
    if existing:
        root = existing[0]
        ensure_layout(root)
        return MemoryLocation(
            root=root,
            db_path=db_path_for(root),
            exists_prior=True,
            durable=True,
            source="detected",
            message=f"Existing ANNE Memory Found: {root}",
        )

    if not allow_temporary:
        fallback = project_fallback or (Path.cwd() / "anne_data")
        return MemoryLocation(
            root=fallback,
            db_path=db_path_for(fallback),
            exists_prior=False,
            durable=False,
            source="temporary",
            message="Kalıcı ANNE Memory bulunamadı.",
        )

    root = project_fallback or (Path.cwd() / "anne_data")
    ensure_layout(root)
    return MemoryLocation(
        root=root,
        db_path=db_path_for(root),
        exists_prior=False,
        durable=False,
        source="temporary",
        message=(
            "Kalıcı ANNE Memory bulunamadı. "
            "Geçici proje klasörü kullanılıyor (kalıcı değil). "
            f"Kalıcı konum için anne_config.env içinde {CONFIG_KEY} ayarlayın."
        ),
    )


def backup_sqlite(db_path: Path, backups_dir: Path | None = None) -> Path | None:
    if not db_path.is_file():
        return None
    dest_dir = backups_dir or (db_path.parent.parent / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / f"anne_memory_{stamp}.sqlite3"
    shutil.copy2(db_path, dest)
    backups = sorted(dest_dir.glob("anne_memory_*.sqlite3"), key=lambda p: p.stat().st_mtime)
    for old in backups[:-10]:
        try:
            old.unlink()
        except OSError:
            pass
    return dest


def safe_connect_note(db_path: Path) -> str:
    if not db_path.exists():
        return "new database will be created"
    size = db_path.stat().st_size
    return f"existing database ({size} bytes)"


__all__ = [
    "CONFIG_KEY",
    "DB_NAME",
    "MemoryLocation",
    "SUBDIRS",
    "backup_sqlite",
    "candidate_drive_roots",
    "db_path_for",
    "discover_existing_anne_roots",
    "ensure_layout",
    "resolve_memory_location",
    "safe_connect_note",
]
