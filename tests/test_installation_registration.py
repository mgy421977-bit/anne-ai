from __future__ import annotations

import json
from pathlib import Path

from anne.setup.installation_registration import load_registration, register_installation


def test_registration_persists_minimal_metadata(tmp_path: Path) -> None:
    record = register_installation(
        root=tmp_path,
        version="0.1.0",
        consent=True,
        email="test@example.com",
    )
    assert record.installation_id
    assert record.installed_version == "0.1.0"
    assert record.notification_consent is True
    assert record.email == "test@example.com"
    loaded = load_registration(tmp_path)
    assert loaded is not None
    assert loaded.installation_id == record.installation_id


def test_registration_declined_contains_no_identity_or_email(tmp_path: Path) -> None:
    record = register_installation(
        root=tmp_path,
        version="0.1.0",
        consent=False,
        email="should-not-be-stored@example.com",
    )
    assert record.notification_consent is False
    assert record.github_user_id is None
    assert record.github_username is None
    assert record.email is None


def test_registration_is_outside_memory_database(tmp_path: Path) -> None:
    record = register_installation(root=tmp_path, version="0.1.0", consent=False)
    payload = json.loads(
        (tmp_path / "installation" / "registration.json").read_text(encoding="utf-8")
    )
    assert payload["installation_id"] == record.installation_id
    assert not (tmp_path / "memory" / "anne_memory.sqlite3").exists()
