"""OpenAI API consultation adapter (api.openai.com) — not ChatGPT Web."""

from __future__ import annotations

import json
import os
from typing import Any

from anne.providers.openai_provider import OpenAIProvider


class ChatGPTConsultationAdapter:
    """Consult ChatGPT via OpenAI HTTP API. Separate from ChatGPT Web / Chrome."""

    source_name = "ChatGPTAPI"

    def __init__(self) -> None:
        self.provider = OpenAIProvider(
            model=os.getenv("ANNE_CHATGPT_MODEL") or os.getenv("ANNE_OPENAI_MODEL")
        )

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "You are a consultation instrument for ANNE AI. Do not speak as ANNE "
            "and do not make decisions for ANNE. Provide a concise factual analysis "
            "that ANNE can independently evaluate. State uncertainty and limitations. "
            "Do not invent sources or claim live web access unless it is actually available.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"ANNE CONTEXT:\n{json.dumps(context, ensure_ascii=False)}"
        )
        try:
            answer = self.provider.ask(prompt)
        except (RuntimeError, ValueError, OSError) as exc:
            return {
                "source": self.source_name,
                "ok": False,
                "error": str(exc),
                "status": "api_error",
                "data": {},
            }
        return {
            "source": self.source_name,
            "ok": bool(answer),
            "status": "ok" if answer else "empty_response",
            "data": {"answer": answer},
        }


__all__ = ["ChatGPTConsultationAdapter"]
