"""xAI / Grok language provider for ANNE (LanguageInterface only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, cast


class XAIProvider:
    """Dependency-free xAI Grok client used only as a language tool."""

    ENDPOINT = "https://api.x.ai/v1/chat/completions"
    DEFAULT_MODEL = "grok-2-latest"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY (or GROK_API_KEY) is required for Grok provider")
        self.model = model or os.getenv("ANNE_XAI_MODEL", self.DEFAULT_MODEL)
        env_timeout = os.getenv("ANNE_XAI_TIMEOUT")
        self.timeout = int(env_timeout) if env_timeout else timeout

    def ask(self, prompt: str, system_instruction: str | None = None) -> str:
        messages: list[dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ANNE-Windows-V1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = cast(dict[str, Any], json.loads(response.read().decode("utf-8")))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"xAI HTTP {exc.code}: {detail[:700]}") from exc
        except TimeoutError as exc:
            raise RuntimeError(f"xAI request timed out after {self.timeout}s") from exc
        return str(
            data.get("choices", [{}])[0].get("message", {}).get("content") or ""
        ).strip()


__all__ = ["XAIProvider"]
