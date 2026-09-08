from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .memory import TranslationMemory
from .providers import LearningProvider


@dataclass(frozen=True)
class TranslationResult:
    speaker: str
    source: str
    direct: str
    semantic: str
    source_mode: str  # memory | learning
    learned: bool


SemanticRenderer = Callable[[str, str, dict[str, Any]], str]


class TranslationEngine:
    """Offline-first English -> Turkish translation orchestration.

    MITOS memory is always checked first. A provider is consulted only for
    unknown text when learning is enabled. The learned record is persisted,
    making subsequent identical expressions provider-free.
    """

    def __init__(
        self,
        memory: TranslationMemory,
        learning_provider: LearningProvider | None = None,
        *,
        learning_enabled: bool = True,
        semantic_renderer: SemanticRenderer | None = None,
    ):
        self.memory = memory
        self.learning_provider = learning_provider
        self.learning_enabled = learning_enabled
        self.semantic_renderer = semantic_renderer

    def translate(
        self,
        source: str,
        *,
        speaker: str = "Unknown",
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        source = source.strip()
        if not source:
            raise ValueError("source text cannot be empty")
        ctx = context or {}

        known = self.memory.lookup(source)
        if known:
            return TranslationResult(
                speaker=speaker,
                source=source,
                direct=str(known["direct"]),
                semantic=str(known.get("semantic", known["direct"])),
                source_mode="memory",
                learned=False,
            )

        if not self.learning_enabled or self.learning_provider is None:
            raise LookupError(
                "Expression is unknown to MITOS and no learning provider is enabled"
            )

        direct = self.learning_provider.translate(source, "en", "tr")
        semantic = (
            self.semantic_renderer(source, direct, ctx)
            if self.semantic_renderer is not None
            else direct
        )
        self.memory.remember(
            source,
            direct,
            semantic,
            context=ctx,
            provider=type(self.learning_provider).__name__,
            confidence=0.85,
        )
        return TranslationResult(
            speaker=speaker,
            source=source,
            direct=direct,
            semantic=semantic,
            source_mode="learning",
            learned=True,
        )
