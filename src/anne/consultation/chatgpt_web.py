"""ChatGPT Web consultation via local Chrome (chatgpt.com).

Uses the user's existing browser session when available. Does not store
passwords, cookies, tokens, or session material in ANNE memory.

This is evidence-only. ANNE remains cognitive authority.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Protocol


CHATGPT_URL = "https://chatgpt.com/"


@dataclass
class WebConsultResult:
    ok: bool
    text: str = ""
    status: str = "ok"
    error: str = ""


class BrowserSession(Protocol):
    """Injectable browser boundary for tests and Playwright implementation."""

    def consult(self, question: str, *, timeout_s: float) -> WebConsultResult: ...

    def close(self) -> None: ...


class ChatGPTWebConsultationAdapter:
    """Consult the public ChatGPT Web UI through Chrome automation.

    Configuration (env):
      ANNE_CHATGPT_WEB_TIMEOUT — seconds (default 90)
      ANNE_CHATGPT_WEB_USER_DATA_DIR — optional Chrome profile dir (session reuse)
      ANNE_CHATGPT_WEB_CHANNEL — chrome|msedge|chromium (default chrome)
    """

    source_name = "ChatGPTWeb"

    def __init__(self, session: BrowserSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
        self.timeout_s = float(os.getenv("ANNE_CHATGPT_WEB_TIMEOUT") or "90")

    def _ensure_session(self) -> BrowserSession:
        if self._session is not None:
            return self._session
        self._session = PlaywrightChromeSession.from_env()
        return self._session

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        _ = context
        try:
            session = self._ensure_session()
        except Exception as exc:  # noqa: BLE001
            return {
                "source": self.source_name,
                "ok": False,
                "status": "browser_unavailable",
                "error": str(exc),
                "data": {},
            }
        try:
            result = session.consult(question, timeout_s=self.timeout_s)
        except Exception as exc:  # noqa: BLE001
            return {
                "source": self.source_name,
                "ok": False,
                "status": "browser_error",
                "error": str(exc),
                "data": {},
            }
        if not result.ok:
            return {
                "source": self.source_name,
                "ok": False,
                "status": result.status,
                "error": result.error or result.status,
                "data": {},
            }
        text = (result.text or "").strip()
        if not text:
            return {
                "source": self.source_name,
                "ok": False,
                "status": "empty_response",
                "error": "ChatGPT Web returned an empty or unreadable response",
                "data": {},
            }
        return {
            "source": self.source_name,
            "ok": True,
            "status": "ok",
            "data": {"answer": text},
        }

    def close(self) -> None:
        if self._owns_session and self._session is not None:
            try:
                self._session.close()
            except Exception:  # noqa: BLE001
                pass
            self._session = None


class PlaywrightChromeSession:
    """Playwright-driven Chrome session against chatgpt.com."""

    def __init__(
        self,
        *,
        user_data_dir: str | None = None,
        channel: str = "chrome",
        headless: bool = False,
    ) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright yüklü değil. Windows: pip install -e '.[chatgpt-web]' "
                "ve sonra: playwright install chrome"
            ) from exc
        self._pw_cm = sync_playwright()
        self._pw = self._pw_cm.__enter__()
        self._user_data_dir = user_data_dir
        self._channel = channel
        self._headless = headless
        self._context = None
        self._page = None
        self._launch()

    @classmethod
    def from_env(cls) -> PlaywrightChromeSession:
        user_data = (os.getenv("ANNE_CHATGPT_WEB_USER_DATA_DIR") or "").strip() or None
        channel = (os.getenv("ANNE_CHATGPT_WEB_CHANNEL") or "chrome").strip() or "chrome"
        headless = (os.getenv("ANNE_CHATGPT_WEB_HEADLESS") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        return cls(user_data_dir=user_data, channel=channel, headless=headless)

    def _launch(self) -> None:
        browser_type = self._pw.chromium
        launch_args: dict[str, Any] = {"headless": self._headless}
        if self._channel and self._channel != "chromium":
            launch_args["channel"] = self._channel
        try:
            if self._user_data_dir:
                self._context = browser_type.launch_persistent_context(
                    self._user_data_dir,
                    **launch_args,
                )
                self._page = (
                    self._context.pages[0]
                    if self._context.pages
                    else self._context.new_page()
                )
            else:
                browser = browser_type.launch(**launch_args)
                self._context = browser.new_context()
                self._page = self._context.new_page()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Chrome başlatılamadı ({self._channel}): {exc}. "
                "Chrome kurulu mu? playwright install chrome çalıştırıldı mı?"
            ) from exc

    def consult(self, question: str, *, timeout_s: float) -> WebConsultResult:
        assert self._page is not None
        page = self._page
        page.set_default_timeout(min(timeout_s * 1000, 120_000))
        try:
            page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        except Exception as exp:  # noqa: BLE001
            return WebConsultResult(ok=False, status="navigation_error", error=str(exp))

        time.sleep(1.0)
        body = ""
        try:
            body = page.content()
        except Exception:  # noqa: BLE001
            pass
        lower = body.lower()

        if self._looks_like_captcha(lower, page):
            return WebConsultResult(
                ok=False,
                status="captcha_or_security",
                error="CAPTCHA or security check detected; refusing to bypass",
            )
        if self._looks_like_login(lower, page):
            return WebConsultResult(
                ok=False,
                status="login_required",
                error="ChatGPT Web session not logged in; open chatgpt.com and sign in first",
            )

        try:
            self._submit_prompt(page, question)
        except Exception as exp:  # noqa: BLE001
            return WebConsultResult(ok=False, status="submit_error", error=str(exp))

        try:
            text = self._wait_for_answer(page, timeout_s)
        except Exception as exp:  # noqa: BLE001
            return WebConsultResult(ok=False, status="timeout", error=str(exp))

        if not text:
            return WebConsultResult(
                ok=False,
                status="empty_response",
                error="Could not read assistant response from ChatGPT Web",
            )
        return WebConsultResult(ok=True, text=text, status="ok")

    def _looks_like_login(self, html_lower: str, page: Any) -> bool:
        markers = (
            "log in",
            "sign in",
            "create account",
            "signup",
            "auth0",
            "welcome to chatgpt",
        )
        if any(m in html_lower for m in markers):
            if self._find_prompt_locator(page) is not None:
                return False
            return True
        return False

    def _looks_like_captcha(self, html_lower: str, page: Any) -> bool:
        markers = ("captcha", "cf-challenge", "challenge-platform", "verify you are human")
        if any(m in html_lower for m in markers):
            return True
        try:
            if page.locator("iframe[src*='captcha'], iframe[src*='challenge']").count() > 0:
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    def _find_prompt_locator(self, page: Any) -> Any | None:
        selectors = [
            "#prompt-textarea",
            "div#prompt-textarea",
            "textarea[data-id='root']",
            "textarea[placeholder*='Message']",
            "textarea[placeholder*='message']",
            "div[contenteditable='true']",
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible():
                    return loc
            except Exception:  # noqa: BLE001
                continue
        return None

    def _submit_prompt(self, page: Any, question: str) -> None:
        loc = self._find_prompt_locator(page)
        if loc is None:
            raise RuntimeError("ChatGPT prompt input not found (UI changed or not ready)")
        loc.click()
        try:
            loc.fill(question)
        except Exception:  # noqa: BLE001
            loc.type(question, delay=10)
        send_selectors = [
            "button[data-testid='send-button']",
            "button[aria-label*='Send']",
            "button[aria-label*='Gönder']",
        ]
        for sel in send_selectors:
            btn = page.locator(sel).first
            try:
                if btn.count() > 0 and btn.is_enabled():
                    btn.click()
                    return
            except Exception:  # noqa: BLE001
                continue
        loc.press("Enter")

    def _wait_for_answer(self, page: Any, timeout_s: float) -> str:
        deadline = time.time() + timeout_s
        last = ""
        while time.time() < deadline:
            if self._looks_like_captcha(page.content().lower(), page):
                raise RuntimeError("CAPTCHA or security check appeared during generation")
            text = self._extract_assistant_text(page)
            if text and text != last and len(text) > 5:
                time.sleep(1.2)
                settled = self._extract_assistant_text(page)
                if settled and len(settled) >= len(text):
                    return settled.strip()
                last = text
            time.sleep(0.6)
        if last:
            return last.strip()
        raise RuntimeError(f"Timed out waiting for ChatGPT Web response ({timeout_s}s)")

    def _extract_assistant_text(self, page: Any) -> str:
        selectors = [
            "[data-message-author-role='assistant']",
            "div[data-message-author-role='assistant']",
            "article[data-testid*='assistant']",
        ]
        chunks: list[str] = []
        for sel in selectors:
            try:
                locs = page.locator(sel)
                n = locs.count()
                if n <= 0:
                    continue
                txt = locs.nth(n - 1).inner_text(timeout=2000)
                if txt and txt.strip():
                    chunks.append(txt.strip())
            except Exception:  # noqa: BLE001
                continue
        if chunks:
            return chunks[-1]
        try:
            md = page.locator(".markdown").last
            if md.count() > 0:
                return str(md.inner_text(timeout=2000)).strip()
        except Exception:  # noqa: BLE001
            pass
        return ""

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._pw_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


__all__ = [
    "CHATGPT_URL",
    "BrowserSession",
    "ChatGPTWebConsultationAdapter",
    "PlaywrightChromeSession",
    "WebConsultResult",
]
