"""Bounded routing policy for optional Turkish language evidence checks.

This policy decides only whether a language lookup is worth attempting. It does
not interpret the lookup, verify its content, or grant any authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.intent import IntentFrame, IntentKind


@dataclass(frozen=True)
class LanguageCheckDecision:
    should_lookup: bool
    reason: str


class TurkishLanguageCheckPolicy:
    """Route language evidence only for explicit high-ambiguity cases."""

    def __init__(self, *, ambiguity_threshold: float = 0.6) -> None:
        if not 0.0 <= ambiguity_threshold <= 1.0:
            raise ValueError("ambiguity_threshold must be between 0.0 and 1.0")
        self.ambiguity_threshold = ambiguity_threshold

    def decide(self, intent: IntentFrame) -> LanguageCheckDecision:
        if intent.intent is IntentKind.GREETING:
            return LanguageCheckDecision(False, "Greeting does not require lexical evidence.")

        if intent.ambiguity >= self.ambiguity_threshold:
            return LanguageCheckDecision(
                True,
                "Explicit intent framing reports high ambiguity; language evidence may clarify context.",
            )

        return LanguageCheckDecision(
            False,
            "Language evidence is not required by the bounded ambiguity threshold.",
        )


__all__ = ["LanguageCheckDecision", "TurkishLanguageCheckPolicy"]
