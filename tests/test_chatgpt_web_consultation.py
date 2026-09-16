"""Mock-browser tests for ChatGPT Web consultation (no real chatgpt.com in CI)."""

from __future__ import annotations

from typing import Any

import pytest

from anne.consultation.chatgpt_web import (
    ChatGPTWebConsultationAdapter,
    WebConsultResult,
)
from anne.consultation.factory import FallbackConsultationAdapter, create_consultation_adapter
from anne.consultation.openai_api import ChatGPTConsultationAdapter


class _MockSession:
    def __init__(self, result: WebConsultResult) -> None:
        self.result = result
        self.closed = False
        self.questions: list[str] = []

    def consult(self, question: str, *, timeout_s: float) -> WebConsultResult:
        self.questions.append(question)
        return self.result

    def close(self) -> None:
        self.closed = True


def test_web_adapter_success() -> None:
    session = _MockSession(WebConsultResult(ok=True, text="Evidence from web UI", status="ok"))
    adapter = ChatGPTWebConsultationAdapter(session=session)
    out = adapter.ask("X nedir?", {})
    assert out["ok"] is True
    assert out["source"] == "ChatGPTWeb"
    assert out["data"]["answer"] == "Evidence from web UI"
    assert session.questions == ["X nedir?"]


def test_web_adapter_login_required() -> None:
    session = _MockSession(
        WebConsultResult(ok=False, status="login_required", error="not logged in")
    )
    out = ChatGPTWebConsultationAdapter(session=session).ask("q", {})
    assert out["ok"] is False
    assert out["status"] == "login_required"
    assert out["data"] == {}


def test_web_adapter_timeout() -> None:
    session = _MockSession(WebConsultResult(ok=False, status="timeout", error="timeout"))
    out = ChatGPTWebConsultationAdapter(session=session).ask("q", {})
    assert out["ok"] is False
    assert out["status"] == "timeout"


def test_web_adapter_browser_error_status() -> None:
    session = _MockSession(WebConsultResult(ok=False, status="browser_error", error="boom"))
    out = ChatGPTWebConsultationAdapter(session=session).ask("q", {})
    assert out["ok"] is False


def test_web_adapter_captcha() -> None:
    session = _MockSession(
        WebConsultResult(ok=False, status="captcha_or_security", error="captcha")
    )
    out = ChatGPTWebConsultationAdapter(session=session).ask("q", {})
    assert out["status"] == "captcha_or_security"
    assert out["ok"] is False


def test_web_adapter_empty_response() -> None:
    session = _MockSession(WebConsultResult(ok=True, text="  ", status="ok"))
    out = ChatGPTWebConsultationAdapter(session=session).ask("q", {})
    assert out["ok"] is False
    assert out["status"] == "empty_response"


def test_api_and_web_adapters_are_distinct() -> None:
    assert ChatGPTConsultationAdapter.source_name != ChatGPTWebConsultationAdapter.source_name


def test_web_result_feeds_as_evidence_shape() -> None:
    session = _MockSession(WebConsultResult(ok=True, text="kanit", status="ok"))
    out = ChatGPTWebConsultationAdapter(session=session).ask("soru", {"known_context": "x"})
    assert out["ok"] is True
    assert "answer" in out["data"]


def test_fallback_to_api_on_web_failure() -> None:
    class _FailWeb:
        def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
            return {"source": "ChatGPTWeb", "ok": False, "status": "timeout", "error": "t"}

    class _OkApi:
        def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
            return {"source": "ChatGPTAPI", "ok": True, "status": "ok", "data": {"answer": "api"}}

    out = FallbackConsultationAdapter(_FailWeb(), _OkApi()).ask("q", {})
    assert out["ok"] is True
    assert out["source"] == "ChatGPTAPI"
    assert out.get("fallback_of") == "ChatGPTWeb"


def test_no_fallback_on_login_by_default() -> None:
    class _LoginWeb:
        def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
            return {
                "source": "ChatGPTWeb",
                "ok": False,
                "status": "login_required",
                "error": "login",
            }

    class _OkApi:
        def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
            return {"source": "ChatGPTAPI", "ok": True, "data": {"answer": "api"}}

    out = FallbackConsultationAdapter(_LoginWeb(), _OkApi()).ask("q", {})
    assert out["ok"] is False
    assert out["status"] == "login_required"


def test_factory_default_auto_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANNE_CONSULTATION_PROVIDER", raising=False)
    monkeypatch.delenv("ANNE_CHATGPT_URL", raising=False)
    monkeypatch.setenv("ANNE_CHATGPT_CONSULTATION", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CHATGPT_API_KEY", raising=False)
    assert create_consultation_adapter() is None


def test_factory_selects_web(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANNE_CONSULTATION_PROVIDER", "chatgpt_web")
    adapter = create_consultation_adapter()
    assert adapter is not None
    assert adapter.__class__.__name__ in {
        "ChatGPTWebConsultationAdapter",
        "FallbackConsultationAdapter",
    }
