from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .memory import MemoryEntry, TranslationMemory
from .providers import TranslationCandidate, TranslationProvider


@dataclass(frozen=True)
class TranslationResult:
    source_text: str
    source_language: str
    target_language: str
    direct: str
    semantic: str
    source: str
    learned: bool
    confidence: float
    context: dict[str, Any] = field(default_factory=dict)


class TranslationEngine:
    """ANNE bilingual engine: memory -> local reasoning -> optional learning.

    Google is never the default runtime translator. It is a learning provider
    used only when the memory misses and learning is explicitly enabled.
    """

    def __init__(
        self,
        memory: TranslationMemory,
        local_provider: TranslationProvider | None = None,
        learning_provider: TranslationProvider | None = None,
        learning_enabled: bool = True,
    ) -> None:
        self.memory = memory
        self.local_provider = local_provider
        self.learning_provider = learning_provider
        self.learning_enabled = learning_enabled

    def translate(
        self,
        text: str,
        source_language: str = "en",
        target_language: str = "tr",
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        context = context or {}
        hit = self.memory.lookup(source_language, target_language, text)
        if hit is not None:
            return TranslationResult(
                source_text=text,
                source_language=source_language,
                target_language=target_language,
                direct=hit.direct_text,
                semantic=hit.semantic_text,
                source="mitos_memory",
                learned=False,
                confidence=hit.confidence,
                context=hit.context,
            )

        candidate: TranslationCandidate | None = None
        learned = False
        if self.learning_enabled and self.learning_provider is not None:
            candidate = self.learning_provider.translate(
                text, source_language, target_language, context
            )
            learned = True

        if self.local_provider is None:
            if candidate is None:
                raise RuntimeError(
                    "No local translation provider is configured and no learning provider is available"
                )
            direct = candidate.direct
            semantic = candidate.direct
            confidence = candidate.confidence
            source = candidate.provider
        else:
            local = self.local_provider.translate(
                text, source_language, target_language, context
            )
            direct = local.direct
            # The local provider can return a structured semantic result later;
            # for now its direct output is the conservative fallback.
            semantic = local.direct
            confidence = local.confidence
            source = local.provider

        self.memory.learn(
            MemoryEntry(
                source_language=source_language,
                target_language=target_language,
                source_text=text,
                direct_text=direct,
                semantic_text=semantic,
                context=context,
                confidence=confidence,
                learned_from=source,
            )
        )

        return TranslationResult(
            source_text=text,
            source_language=source_language,
            target_language=target_language,
            direct=direct,
            semantic=semantic,
            source=source,
            learned=learned,
            confidence=confidence,
            context=context,
        )
