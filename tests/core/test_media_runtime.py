from pathlib import Path

from anne.core.local_media import LocalMediaLauncher
from anne.core.media_context import MediaContext
from anne.core.workload_scheduler import WorkItem, WorkloadPriority, WorkloadScheduler


def test_media_context_formats_position_and_prompt(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"test")
    context = MediaContext.from_path(media, position_seconds=3723, scene_label="Scene A")
    assert context.position_label == "01:02:03"
    prompt = context.discussion_prompt("Why did the character do this?")
    assert "01:02:03" in prompt
    assert "Scene A" in prompt
    assert "Why did the character do this?" in prompt


def test_media_launcher_does_not_require_a_specific_player(tmp_path: Path) -> None:
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"test")
    launcher = LocalMediaLauncher(player_command="definitely-not-installed")
    assert launcher.available_player() is None
    assert launcher.can_open(media)


def test_scheduler_yields_background_work_under_pressure() -> None:
    scheduler = WorkloadScheduler()
    scheduler.submit(
        WorkItem("bg", "background", lambda: "bg", WorkloadPriority.BACKGROUND)
    )
    assert scheduler.choose(host_pressure=0.90) is None


def test_scheduler_prefers_interactive_work() -> None:
    scheduler = WorkloadScheduler()
    scheduler.submit(
        WorkItem("bg", "background", lambda: "bg", WorkloadPriority.BACKGROUND)
    )
    scheduler.submit(
        WorkItem("ui", "interactive", lambda: "ui", WorkloadPriority.INTERACTIVE)
    )
    assert scheduler.choose(host_pressure=0.90).id == "ui"
