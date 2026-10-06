"""Read-only Dropbox knowledge adapter for ANNE.

The adapter is deliberately outside the cognitive core. Dropbox is treated as
an external knowledge source, not as ANNE's memory or epistemic authority.

Authentication uses Dropbox OAuth 2.0 with PKCE and offline access. The local
credential file stores the refresh token with restrictive permissions where
the platform supports them.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import dropbox
    from dropbox import files, oauth
except ImportError as exc:  # pragma: no cover - exercised when optional extra is absent
    raise ImportError(
        "Dropbox support requires the optional dependency. "
        'Install with: python -m pip install -e ".[cloud]"'
    ) from exc


READ_SCOPES = ("files.metadata.read", "files.content.read")


@dataclass(frozen=True)
class DropboxConfig:
    """Configuration for the ANNE Dropbox read-only knowledge layer."""

    app_key: str
    token_path: Path = Path("~/.anne/dropbox_token.json").expanduser()
    root_path: str = "/ANNE"
    max_download_bytes: int = 25 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "DropboxConfig":
        app_key = os.environ.get("ANNE_DROPBOX_APP_KEY", "").strip()
        if not app_key:
            raise ValueError("ANNE_DROPBOX_APP_KEY is required")
        token_path = Path(
            os.environ.get(
                "ANNE_DROPBOX_TOKEN_PATH",
                "~/.anne/dropbox_token.json",
            )
        ).expanduser()
        root_path = os.environ.get("ANNE_DROPBOX_ROOT", "/ANNE").strip() or "/ANNE"
        return cls(app_key=app_key, token_path=token_path, root_path=root_path)


@dataclass(frozen=True)
class DropboxDocument:
    """Minimal source metadata exposed to ANNE's knowledge layer."""

    path: str
    name: str
    file_id: str
    size: int
    modified_time: str
    source: str = "dropbox"


class DropboxKnowledgeAdapter:
    """Read-only Dropbox adapter.

    It can authenticate, list files, search filenames locally in the returned
    Dropbox index, and download selected documents. It does not write to
    Dropbox and does not write directly to FractalMemory.
    """

    def __init__(self, config: DropboxConfig, client: dropbox.Dropbox) -> None:
        self.config = config
        self.client = client

    @classmethod
    def connect(cls, config: DropboxConfig | None = None) -> "DropboxKnowledgeAdapter":
        config = config or DropboxConfig.from_env()
        token = cls._load_token(config.token_path)
        if not token:
            raise RuntimeError(
                "Dropbox is not authorized for ANNE. Run 'anne-dropbox-auth' first."
            )

        client = dropbox.Dropbox(
            oauth2_refresh_token=token["refresh_token"],
            app_key=config.app_key,
            scope=list(READ_SCOPES),
            user_agent="ANNE-AI/0.1",
        )
        client.users_get_current_account()
        return cls(config, client)

    @classmethod
    def authorize(cls, config: DropboxConfig | None = None) -> dict[str, str]:
        """Run a local PKCE OAuth flow and persist only the refresh token."""

        config = config or DropboxConfig.from_env()
        flow = oauth.DropboxOAuth2FlowNoRedirect(
            config.app_key,
            token_access_type="offline",
            scope=list(READ_SCOPES),
            use_pkce=True,
        )
        print("Open this URL in your browser and authorize ANNE:")
        print(flow.start())
        code = input("Paste the Dropbox authorization code: ").strip()
        if not code:
            raise ValueError("Dropbox authorization code cannot be empty")

        result = flow.finish(code)
        payload = {
            "refresh_token": result.refresh_token,
            "account_id": result.account_id,
            "scope": list(result.scope),
            "authorized_at": datetime.now(timezone.utc).isoformat(),
        }
        config.token_path.parent.mkdir(parents=True, exist_ok=True)
        config.token_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        try:
            config.token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return {"account_id": result.account_id, "token_path": str(config.token_path)}

    @staticmethod
    def _load_token(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        refresh_token = data.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError(f"Invalid Dropbox token file: {path}")
        return data

    def list_documents(self, root_path: str | None = None) -> list[DropboxDocument]:
        """List files recursively below the configured ANNE root."""

        path = root_path or self.config.root_path
        documents: list[DropboxDocument] = []
        result = self.client.files_list_folder(path, recursive=True)
        while True:
            for entry in result.entries:
                if isinstance(entry, files.FileMetadata):
                    documents.append(
                        DropboxDocument(
                            path=entry.path_display or entry.path_lower or entry.name,
                            name=entry.name,
                            file_id=entry.id,
                            size=entry.size,
                            modified_time=entry.server_modified.isoformat(),
                        )
                    )
            if not result.has_more:
                break
            result = self.client.files_list_folder_continue(result.cursor)
        return documents

    def search(self, query: str, root_path: str | None = None) -> list[DropboxDocument]:
        """Search filenames after listing the configured knowledge root.

        This intentionally performs local matching so the adapter also works
        with Dropbox Basic, where Dropbox's server-side content search is
        restricted. Content extraction remains a separate future layer.
        """

        needle = query.casefold().strip()
        if not needle:
            return []
        return [
            document
            for document in self.list_documents(root_path)
            if needle in document.name.casefold()
            or needle in document.path.casefold()
        ]

    def download(self, document: DropboxDocument, destination: Path) -> Path:
        """Download one document with a bounded local size policy."""

        if document.size > self.config.max_download_bytes:
            raise ValueError(
                f"Refusing to download {document.path}: "
                f"{document.size} bytes exceeds the configured limit "
                f"of {self.config.max_download_bytes} bytes"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.files_download_to_file(str(destination), document.path)
        return destination

    def pull(self, query: str, destination_root: Path) -> list[Path]:
        """Download all filename matches below the ANNE root."""

        downloaded: list[Path] = []
        for document in self.search(query):
            safe_name = Path(document.name).name
            target = destination_root / safe_name
            downloaded.append(self.download(document, target))
        return downloaded
