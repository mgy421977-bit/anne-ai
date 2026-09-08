from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TranslationCandidate:
    direct: str
    provider: str
    confidence: float = 0.0
    metadata: dict[str, Any] | None = None


class TranslationProvider(Protocol):
    def translate(self, text: str, source_language: str, target_language: str,
                  context: dict[str, Any] | None = None) -> TranslationCandidate: ...


class GoogleTranslationProvider:
    """Google Cloud Translation adapter used only for learning/bootstrapping."""

    def __init__(self, project_id: str | None = None, location: str = "global") -> None:
        import os
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._client: Any = None

    def _client_or_create(self) -> Any:
        if self._client is None:
            from google.cloud import translate_v3
            self._client = translate_v3.TranslationServiceClient()
        return self._client

    def translate(self, text: str, source_language: str, target_language: str,
                  context: dict[str, Any] | None = None) -> TranslationCandidate:
        if not self.project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Google learning mode")
        client = self._client_or_create()
        parent = f"projects/{self.project_id}/locations/{self.location}"
        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source_language,
                "target_language_code": target_language,
            }
        )
        return TranslationCandidate(
            direct=response.translations[0].translated_text,
            provider="google_cloud_translation",
            confidence=0.75,
            metadata={"context": context or {}},
        )


class LocalTranslationProvider:
    """Local LLM adapter. The model is deliberately injected by the caller."""

    def __init__(self, model: Any) -> None:
        self.model = model

    def translate(self, text: str, source_language: str, target_language: str,
                  context: dict[str, Any] | None = None) -> TranslationCandidate:
        prompt = (
            "Translate without adding facts. Preserve tense, negation, modality, "
            "conditions, technical terminology and speaker intent. Return only the "
            "translation.\n\n"
            f"Context: {context or {}}\n"
            f"{source_language}->{target_language}: {text}"
        )
        result = self.model(prompt)
        return TranslationCandidate(
            direct=str(result).strip(),
            provider="local_model",
            confidence=0.70,
            metadata={"context": context or {}},
        )
