from pathlib import Path

from anne.core.decision_loop import DecisionLoop


def test_decision_loop_exposes_execution_boundary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("anne.core.windows_execution.platform.system", lambda: "Linux")
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    result = loop.run("test a bounded execution plan")
    execution = result.output["resource_decision"]["windows_execution"]

    assert execution["status"] == "UNAVAILABLE"
    assert execution["requires_authorization"] is True
