"""Minimal ANNE Desktop bootstrapper.

The bootstrapper initializes local state first, then performs a best-effort
release check. Network failure is deliberately non-fatal.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from anne.desktop.updater import fetch_manifest, is_newer
from anne.desktop.workspace import ANNEWorkspace

CURRENT_VERSION = "0.1.0"
CONFIG_FILE = Path(__file__).with_name("config.json")


def load_config() -> dict[str, object]:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def resolve_data_dir(config: dict[str, object]) -> Path:
    configured = os.environ.get("ANNE_DATA_DIR") or str(config.get("data_dir", ""))
    configured = os.path.expandvars(configured).strip()
    return Path(configured) if configured else Path.home() / "ANNE" / "data"


def main() -> None:
    config = load_config()
    workspace = ANNEWorkspace(resolve_data_dir(config))
    workspace.initialize()

    if bool(config.get("update_check_on_start", True)):
        try:
            manifest = fetch_manifest()
            if is_newer(CURRENT_VERSION, manifest.version):
                print(f"ANNE update available: {manifest.version}")
        except Exception as exc:
            # Offline-first means update discovery can never prevent startup.
            print(f"Update check skipped: {exc}")

    print(f"ANNE {CURRENT_VERSION} ready")
    print(f"Local workspace: {workspace.root}")
    print("Offline-first runtime initialized.")


if __name__ == "__main__":
    main()
