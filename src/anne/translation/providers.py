from __future__ import annotations

import os
from typing import Protocol


class LearningProvider(Protocol):
    def translate(self, text: str, source: str = "en", target: str = "tr") -> str: ...


class GoogleCloudTranslationProvider:
    """Optional Google Cloud Translation learning provider.

    This provider is intentionally used only for unknown expressions. The
    caller owns the offline-first policy and persistent learning decision.
    """

    def __init__(self, project_id: str | None = None, location: str = "global"):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._client = None

    def translate(self, text: str, source: str = "en", target: str = "tr") -> str:
        if not self.project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
        if self._client is None:
            from google.cloud import translate_v3

            self._client = translate_v3.TranslationServiceClient()
        parent = f"projects/{self.project_id}/locations/{self.location}"
        response = self._client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source,
                "target_language_code": target,
            }
        )
        return response.translations[0].translated_text
