"""Select consultation adapter without mixing API and Web responsibilities."""

from __future__ import annotations

import os
from typing import Any, Protocol


class ConsultationAdapter(Protocol):
    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]: ...


def _truthy(name: str, default: str = "") -> bool:
    return (os.getenv(name) or default).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_provider(raw: str) -> str:
    name = raw.strip().lower().replace("-", "_")
    aliases = {
        "openai": "openai_api",
        "api": "openai_api",
        "chatgpt_api": "openai_api",
        "chatgpt": "openai_api",
        "web": "chatgpt_web",
        "chatgpt_web": "chatgpt_web",
        "chrome": "chatgpt_web",
        "http": "http",
        "none": "none",
        "off": "none",
        "": "auto",
    }
    return aliases.get(name, name)


class _HttpConsultationAdapter:
    """POST JSON consultation to ANNE-controlled HTTP endpoint (not chatgpt.com)."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.source_name = "RESEARCH"

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        import json
        from urllib.error import URLError
        from urllib.request import Request, urlopen

        payload_question = f"{question}\n\nCONTEXT:\n{json.dumps(context, ensure_ascii=False)}"
        body = json.dumps({"question": payload_question}, ensure_ascii=False).encode()
        request = Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            return {
                "source": self.source_name,
                "ok": False,
                "error": str(exc),
                "status": "http_error",
            }
        return {"source": self.source_name, "ok": True, "status": "ok", "data": data}


class FallbackConsultationAdapter:
    """Try primary consultation; on hard failure optionally try fallback."""

    def __init__(
        self,
        primary: ConsultationAdapter,
        fallback: ConsultationAdapter | None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        result = self.primary.ask(question, context)
        if result.get("ok"):
            return result
        if self.fallback is None:
            return result
        status = str(result.get("status") or "")
        if status in {"login_required", "captcha_or_security"} and not _truthy(
            "ANNE_CONSULTATION_FALLBACK_ON_AUTH", "false"
        ):
            return result
        secondary = self.fallback.ask(question, context)
        secondary = dict(secondary)
        secondary["fallback_of"] = result.get("source")
        secondary["primary_status"] = status
        secondary["primary_error"] = result.get("error")
        return secondary


def create_consultation_adapter() -> ConsultationAdapter | None:
    """Build consultation instrument from env. Default preserves V1 API behaviour."""
    explicit = _normalize_provider(os.getenv("ANNE_CONSULTATION_PROVIDER") or "")
    http_url = (os.getenv("ANNE_CHATGPT_URL") or "").strip()
    legacy_api = _truthy("ANNE_CHATGPT_CONSULTATION", "true")

    if explicit == "none":
        return None

    def _api() -> ConsultationAdapter | None:
        try:
            from anne.consultation.openai_api import ChatGPTConsultationAdapter

            return ChatGPTConsultationAdapter()
        except (ValueError, RuntimeError, ImportError):
            return None

    def _web() -> ConsultationAdapter | None:
        try:
            from anne.consultation.chatgpt_web import ChatGPTWebConsultationAdapter

            return ChatGPTWebConsultationAdapter()
        except (ValueError, RuntimeError, ImportError):
            return None

    def _http() -> ConsultationAdapter | None:
        if not http_url:
            return None
        return _HttpConsultationAdapter(http_url)

    primary: ConsultationAdapter | None = None
    if explicit == "chatgpt_web":
        primary = _web()
    elif explicit == "openai_api":
        primary = _api()
    elif explicit == "http":
        primary = _http()
    else:
        primary = _http() or (_api() if legacy_api else None)

    if primary is None:
        return None

    fallback_name = _normalize_provider(os.getenv("ANNE_CONSULTATION_FALLBACK") or "none")
    fallback: ConsultationAdapter | None = None
    if fallback_name == "openai_api" and explicit != "openai_api":
        fallback = _api()
    elif fallback_name == "chatgpt_web" and explicit != "chatgpt_web":
        fallback = _web()

    if fallback is not None:
        return FallbackConsultationAdapter(primary, fallback)
    return primary


__all__ = [
    "ConsultationAdapter",
    "FallbackConsultationAdapter",
    "create_consultation_adapter",
]
