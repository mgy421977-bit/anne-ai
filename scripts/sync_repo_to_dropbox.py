"""Mirror the checked-out ANNE AI repository into Dropbox.

This script is intended for CI or a trusted local workstation. It mirrors
repository files into /ANNE AI while skipping .git metadata. Dropbox is a
backup/knowledge surface; GitHub remains the source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path

import dropbox
from dropbox.files import WriteMode


ROOT = Path(__file__).resolve().parents[1]
DROPBOX_ROOT = os.environ.get("ANNE_DROPBOX_SYNC_ROOT", "/ANNE AI")
REFRESH_TOKEN = os.environ["ANNE_DROPBOX_SYNC_REFRESH_TOKEN"]
APP_KEY = os.environ["ANNE_DROPBOX_APP_KEY"]

SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
MAX_SIMPLE_UPLOAD = 150 * 1024 * 1024


def client() -> dropbox.Dropbox:
    return dropbox.Dropbox(
        oauth2_refresh_token=REFRESH_TOKEN,
        app_key=APP_KEY,
        scope=["files.content.write", "files.metadata.write"],
        user_agent="ANNE-AI-RepoSync/1.0",
    )


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix().casefold())


def upload_file(dbx: dropbox.Dropbox, source: Path) -> None:
    rel = source.relative_to(ROOT).as_posix()
    target = f"{DROPBOX_ROOT.rstrip('/')}/{rel}"
    size = source.stat().st_size
    with source.open("rb") as handle:
        if size <= MAX_SIMPLE_UPLOAD:
            dbx.files_upload(
                handle.read(),
                target,
                mode=WriteMode.overwrite,
                mute=True,
            )
            return

        session = dbx.files_upload_session_start(handle.read(8 * 1024 * 1024))
        offset = 8 * 1024 * 1024
        while offset < size:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            close = offset + len(chunk) >= size
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session.session_id,
                offset=offset,
            )
            if close:
                dbx.files_upload_session_finish(
                    chunk,
                    cursor,
                    dropbox.files.CommitInfo(path=target, mode=WriteMode.overwrite, mute=True),
                )
            else:
                dbx.files_upload_session_append_v2(chunk, cursor)
            offset += len(chunk)


def main() -> None:
    dbx = client()
    dbx.users_get_current_account()
    files = iter_files()
    print(f"Syncing {len(files)} files to {DROPBOX_ROOT}")
    for index, source in enumerate(files, start=1):
        upload_file(dbx, source)
        print(f"[{index}/{len(files)}] {source.relative_to(ROOT)}")
    print("Dropbox sync completed.")


if __name__ == "__main__":
    main()
