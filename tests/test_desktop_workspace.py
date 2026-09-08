from pathlib import Path

from anne.desktop.workspace import ANNEWorkspace


def test_workspace_initializes_local_tree(tmp_path: Path) -> None:
    workspace = ANNEWorkspace(tmp_path / "anne-data")
    workspace.initialize()
    meeting = workspace.meeting("2026-09-08_21-55")

    assert workspace.db_path.exists()
    assert meeting.audio_file.parent.exists()
    assert meeting.transcript_file.parent.exists()
    assert meeting.direct_translation_file.parent.exists()
    assert meeting.semantic_translation_file.parent.exists()
    assert meeting.report_file.parent.exists()


def test_workspace_appends_unicode_jsonl(tmp_path: Path) -> None:
    workspace = ANNEWorkspace(tmp_path / "anne-data")
    meeting = workspace.meeting("m1")
    meeting.append_transcript({"speaker": "Gürhan", "text": "Merhaba dünya"})

    line = meeting.transcript_file.read_text(encoding="utf-8").strip()
    assert "Gürhan" in line
    assert "Merhaba dünya" in line


def test_disk_status_is_reported(tmp_path: Path) -> None:
    workspace = ANNEWorkspace(tmp_path / "anne-data")
    workspace.initialize()
    status = workspace.disk_status(minimum_free_gb=0.0)
    assert status["safe"] is True
    assert float(status["free_gb"]) >= 0
