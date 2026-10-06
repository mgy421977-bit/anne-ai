from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from anne.cloud.dropbox import DropboxConfig, DropboxDocument, DropboxKnowledgeAdapter


class FakeDropbox:
    def __init__(self) -> None:
        self.downloaded: list[tuple[str, str]] = []

    def files_list_folder(self, path: str, recursive: bool = True):
        class Result:
            has_more = False
            cursor = "cursor"
            entries = [
                type(
                    "File",
                    (),
                    {
                        "path_display": "/ANNE/RESEARCH/notes.txt",
                        "path_lower": "/anne/research/notes.txt",
                        "name": "notes.txt",
                        "id": "id:notes",
                        "size": 42,
                        "server_modified": datetime(2026, 10, 6, tzinfo=timezone.utc),
                    },
                )()
            ]

        assert path == "/ANNE"
        assert recursive is True
        return Result()

    def files_download_to_file(self, destination: str, path: str) -> None:
        self.downloaded.append((destination, path))


def test_list_documents_is_read_only_and_structured() -> None:
    adapter = DropboxKnowledgeAdapter(
        DropboxConfig(app_key="test"),
        FakeDropbox(),  # type: ignore[arg-type]
    )

    documents = adapter.list_documents()

    assert len(documents) == 1
    assert documents[0].name == "notes.txt"
    assert documents[0].source == "dropbox"


def test_search_matches_filename_without_server_content_search() -> None:
    adapter = DropboxKnowledgeAdapter(
        DropboxConfig(app_key="test"),
        FakeDropbox(),  # type: ignore[arg-type]
    )

    assert [item.name for item in adapter.search("NOTES")] == ["notes.txt"]


def test_download_enforces_size_limit(tmp_path: Path) -> None:
    client = FakeDropbox()
    adapter = DropboxKnowledgeAdapter(
        DropboxConfig(app_key="test", max_download_bytes=10),
        client,  # type: ignore[arg-type]
    )
    document = DropboxDocument(
        path="/ANNE/large.pdf",
        name="large.pdf",
        file_id="id:large",
        size=11,
        modified_time="2026-10-06T00:00:00+00:00",
    )

    try:
        adapter.download(document, tmp_path / "large.pdf")
    except ValueError as exc:
        assert "exceeds" in str(exc)
    else:
        raise AssertionError("oversized downloads must be rejected")
