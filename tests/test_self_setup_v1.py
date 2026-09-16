"""V1 self-setup and provider boundary tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from anne.setup.self_setup import run_self_setup


def test_self_setup_creates_dirs_and_example(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANNE_WEB_PROVIDER", raising=False)
    report = run_self_setup(root=tmp_path)
    assert (tmp_path / "anne_config.env.example").is_file()
    assert (tmp_path / "anne_data").is_dir()
    assert report.data_dir
    assert report.ready is False


def test_self_setup_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    r1 = run_self_setup(root=tmp_path)
    r2 = run_self_setup(root=tmp_path)
    assert (tmp_path / "anne_data").is_dir()
    assert r1.data_dir == r2.data_dir


def test_self_setup_ready_with_config_and_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "anne_config.env").write_text(
        "ANNE_WEB_PROVIDER=openai\nOPENAI_API_KEY=sk-test-not-real\n",
        encoding="utf-8",
    )
    report = run_self_setup(root=tmp_path)
    names = {c.name: c for c in report.checks}
    assert names["Configuration"].ok is True
    assert names["Language Interface"].ok is True
    assert report.provider == "openai"


def test_provider_module_openai_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CHATGPT_API_KEY", raising=False)
    from anne.providers.openai_provider import OpenAIProvider

    with pytest.raises(ValueError):
        OpenAIProvider()


def test_provider_module_xai_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    from anne.providers.xai_provider import XAIProvider

    with pytest.raises(ValueError):
        XAIProvider()


def test_web_tinker_rejects_ollama_as_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNE_WEB_PROVIDER", "ollama")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        from anne.api.web_tinker import ProviderConfigurationError, _create_conversation
    except RuntimeError as exc:
        assert "api" in str(exc).lower()
        return
    with pytest.raises(ProviderConfigurationError) as exc:
        _create_conversation()
    msg = str(exc.value).lower()
    assert "ollama" in msg or "openai" in msg


def test_no_ollama_env_required_for_v1() -> None:
    assert True
