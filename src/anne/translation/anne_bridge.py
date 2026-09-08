from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .engine import TranslationEngine, TranslationResult


@dataclass(frozen=True)
class TranslationObservation:
    speaker: str
    text: str
    source_language: str
    target_language: str
    meeting_id: str | None = None
    topic: str | None = None


class AnneTranslationBridge:
    """Connects live translation to ANNE's cognitive sequence.

    DUY: receive the utterance unchanged.
    BAK: attach speaker/session context and query MITOS memory.
    GÖR: preserve terminology/context signals supplied by the caller.
    ANLA: run the bilingual translation engine.
    HİSSET: intentionally does not alter factual content; tone/context remain metadata.
    YAP: return a traceable result for the UI or meeting recorder.
    """

    def __init__(self, engine: TranslationEngine) -> None:
        self.engine = engine

    def process(self, observation: TranslationObservation) -> TranslationResult:
        context: dict[str, Any] = {
            "speaker": observation.speaker,
            "meeting_id": observation.meeting_id,
            "topic": observation.topic,
            "pipeline": ["DUY", "BAK", "GÖR", "ANLA", "HİSSET", "YAP"],
        }
        return self.engine.translate(
            observation.text,
            source_language=observation.source_language,
            target_language=observation.target_language,
            context=context,
        )
