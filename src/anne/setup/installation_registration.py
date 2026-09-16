"""Optional, privacy-preserving ANNE installation registration.

This module records only installation metadata and explicit notification consent.
It never stores conversation, memory, experience, research content, API keys, or
OAuth tokens. A future notification service can consume the registration payload.

GitHub account discovery is intentionally optional and uses an already-authenticated
GitHub CLI session when available. No credentials are persisted by ANNE.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class InstallationRecord:
    installation_id: str
    github_user_id: int | None
    github_username: str | None
    installed_version: str
    installed_at: str
    notification_consent: bool
    consent_at: str | None
    email: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _installation_id(path: Path) -> str:
    existing = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    if existing:
        return existing
    value = str(uuid.uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return value


def _github_identity() -> tuple[int | None, str | None]:
    """Return the active GitHub CLI identity without persisting credentials."""
    if shutil.which("gh") is None:
        return None, None
    try:
        proc = subprocess.run(
            ["gh", "api", "user", "--jq", ".id + \"\\t\" + .login"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    parts = proc.stdout.strip().split("\t", 1)
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), parts[1]
    except ValueError:
        return None, None


def register_installation(
    *,
    root: Path,
    version: str,
    consent: bool,
    email: str | None = None,
) -> InstallationRecord:
    """Create/update a local registration record after explicit consent."""
    registration_dir = root / "installation"
    id_path = registration_dir / "installation_id"
    record_path = registration_dir / "registration.json"
    installation_id = _installation_id(id_path)
    github_user_id, github_username = _github_identity() if consent else (None, None)
    record = InstallationRecord(
        installation_id=installation_id,
        github_user_id=github_user_id,
        github_username=github_username,
        installed_version=version,
        installed_at=_now(),
        notification_consent=consent,
        consent_at=_now() if consent else None,
        email=email if consent and email else None,
    )
    registration_dir.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(record.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def load_registration(root: Path) -> InstallationRecord | None:
    path = root / "installation" / "registration.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return InstallationRecord(**data)
    except (OSError, TypeError, ValueError):
        return None


def maybe_register_installation(root: Path, version: str) -> InstallationRecord | None:
    """Interactive first-run registration; never blocks ANNE when declined."""
    if (os.getenv("ANNE_GITHUB_REGISTER") or "").strip().lower() not in {"1", "true", "yes"}:
        return load_registration(root)
    existing = load_registration(root)
    if existing is not None:
        return existing

    print()
    print("ANNE Installation Registration (optional)")
    print("GitHub account linking is optional and does not send ANNE memory or conversations.")
    answer = input("Link this installation to your GitHub account for future version notices? [y/N]: ")
    consent = answer.strip().lower() in {"y", "yes"}
    email = None
    if consent:
        email_value = input("Optional notification email (leave blank to skip): ").strip()
        email = email_value or None
    return register_installation(root=root, version=version, consent=consent, email=email)


def main() -> int:
    root = Path(os.getenv("ANNE_MEMORY_ROOT") or os.getcwd()).resolve()
    version = os.getenv("ANNE_VERSION", "0.1.0")
    record = maybe_register_installation(root, version)
    if record is not None:
        identity = record.github_username or "not linked"
        print(f"  Installation: {record.installation_id}")
        print(f"  GitHub: {identity}")
        print(f"  Notifications: {'enabled' if record.notification_consent else 'disabled'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
