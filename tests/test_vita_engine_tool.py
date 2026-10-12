from pathlib import Path

import pytest

from anne.tools.vita_engine import VitaEngineTool


def test_vita_tool_requires_explicit_trusted_checkout(monkeypatch):
    monkeypatch.delenv("VITA_ENGINE_PATH", raising=False)
    with pytest.raises(RuntimeError, match="VITA_ENGINE_PATH"):
        VitaEngineTool()


def test_vita_tool_rejects_checkout_without_adapter(tmp_path: Path):
    (tmp_path / "api").mkdir()
    with pytest.raises(FileNotFoundError, match="VITA-Engine adapter not found"):
        VitaEngineTool(tmp_path)
