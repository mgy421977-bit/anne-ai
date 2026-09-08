from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LanguageCode = Literal["en", "tr"]


@dataclass(frozen=True)
class LanguageProfile:
    code: LanguageCode
    name: str
    grammar_notes: tuple[str, ...]
    temporal_markers: tuple[str, ...]


ENGLISH = LanguageProfile(
    code="en",
    name="English",
    grammar_notes=(
        "tense and aspect",
        "modal verbs",
        "conditionals",
        "phrasal verbs",
        "articles and determiners",
    ),
    temporal_markers=("already", "still", "yet", "since", "for", "by", "until"),
)

TURKISH = LanguageProfile(
    code="tr",
    name="Türkçe",
    grammar_notes=(
        "agglutinative suffixes",
        "tense/aspect/evidentiality",
        "case and agreement",
        "conditionals",
        "word-order-sensitive emphasis",
    ),
    temporal_markers=("zaten", "hâlâ", "henüz", "-den beri", "-dır", "kadar", "dek"),
)

PROFILES = {"en": ENGLISH, "tr": TURKISH}


def profile(language: LanguageCode) -> LanguageProfile:
    return PROFILES[language]


def reverse_pair(source: LanguageCode, target: LanguageCode) -> tuple[str, str]:
    if source == target:
        raise ValueError("source and target languages must differ")
    return source, target
