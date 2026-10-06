"""Deterministic consistency checks for user requests.

This gate checks whether explicit requirements inside a request conflict with
each other. It does not establish factual truth and does not replace evidence
verification or ambiguity handling.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RequestConsistencyResult:
    """Conservative result of checking a request's internal consistency."""

    status: str  # CONSISTENT | INCONSISTENT | UNDETERMINED
    action: str  # CONTINUE | REFRAME | REVIEW
    contradictions: tuple[str, ...] = ()
    reason: str = ""


class RequestConsistencyGate:
    """Check explicit internal requirement conflicts without truth claims."""

    _NEGATION = re.compile(
        r"\b(?:değil|değildir|yapma|etme|olmasın|olamaz|not|never|without)\b",
        re.IGNORECASE,
    )
    _COMMAND = re.compile(
        r"\b(?:yap|et|oluştur|değiştir|sil|ekle|kaldır|göster|ver|kullan|"
        r"make|do|create|change|delete|add|remove|show|use)\b",
        re.IGNORECASE,
    )

    @classmethod
    def evaluate(cls, raw_input: str) -> RequestConsistencyResult:
        text = " ".join(raw_input.strip().split())
        if not text:
            return RequestConsistencyResult(
                "UNDETERMINED", "REVIEW", reason="empty_request"
            )

        positive_actions = {
            cls._canonical_action(m.group(0))
            for m in cls._COMMAND.finditer(text)
            if not cls._is_negated(text, m.start())
        }
        negative_actions = {
            cls._canonical_action(m.group(0))
            for m in cls._COMMAND.finditer(text)
            if cls._is_negated(text, m.start())
        }

        overlap = sorted(positive_actions & negative_actions)
        contradictions = [
            f"same_action_both_required_and_forbidden:{action}"
            for action in overlap
        ]

        if contradictions:
            return RequestConsistencyResult(
                "INCONSISTENT",
                "REFRAME",
                tuple(contradictions),
                "request_contains_conflicting_requirements",
            )

        return RequestConsistencyResult(
            "CONSISTENT",
            "CONTINUE",
            reason="no_explicit_internal_conflict_detected",
        )

    @staticmethod
    def _canonical_action(action: str) -> str:
        value = action.lower()
        mapping = {
            "oluştur": "create",
            "yap": "do",
            "et": "do",
            "değiştir": "change",
            "sil": "delete",
            "ekle": "add",
            "kaldır": "remove",
            "göster": "show",
            "ver": "provide",
            "kullan": "use",
        }
        return mapping.get(value, value)

    @classmethod
    def _is_negated(cls, text: str, start: int) -> bool:
        window = text[max(0, start - 24):start]
        return bool(cls._NEGATION.search(window))
