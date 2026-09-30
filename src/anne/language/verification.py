"""Bounded corroboration for non-authoritative language observations.

Language corroboration is intentionally separate from factual verification.
Two independent sources may corroborate an identical lexical observation, but
the result never becomes factual truth or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from anne.language.evidence import LanguageEvidence, LanguageLookupResult


class LanguageVerificationStatus(StrEnum):
    """Scoped status for lexical-source agreement only."""

    CORROBORATED = "corroborated"
    DIVERGENT = "divergent"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class LanguageVerificationResult:
    """Result scoped to lexical corroboration, never general factual truth."""

    status: LanguageVerificationStatus
    query: str
    source_refs: tuple[str, ...] = ()
    independent_sources: tuple[str, ...] = ()
    matched_meanings: tuple[str, ...] = ()
    reason: str = ""

    @property
    def authoritative(self) -> bool:
        return False

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "query": self.query,
            "source_refs": self.source_refs,
            "independent_sources": self.independent_sources,
            "matched_meanings": self.matched_meanings,
            "reason": self.reason,
            "authoritative": False,
        }


class LanguageEvidenceVerifier:
    """Compare lexical observations only when provenance is independently scoped."""

    def verify(
        self,
        query: str,
        results: tuple[LanguageLookupResult, ...],
    ) -> LanguageVerificationResult:
        normalized_query = " ".join(str(query).split()).casefold()
        if not normalized_query:
            return LanguageVerificationResult(
                LanguageVerificationStatus.INSUFFICIENT,
                normalized_query,
                reason="Empty language query.",
            )

        observations: list[tuple[str, str, str]] = []
        for result in results:
            for item in result.evidence:
                if " ".join(item.query.split()).casefold() != normalized_query:
                    continue
                identity = self._source_identity(result.provider, item)
                if not identity:
                    continue
                meaning = self._normalize_meaning(item.meaning)
                if meaning:
                    observations.append((identity, item.source_ref, meaning))

        by_source: dict[str, set[str]] = {}
        refs: dict[str, set[str]] = {}
        for identity, source_ref, meaning in observations:
            by_source.setdefault(identity, set()).add(meaning)
            refs.setdefault(identity, set()).add(source_ref)

        independent = tuple(sorted(by_source))
        source_refs = tuple(sorted({ref for values in refs.values() for ref in values}))
        meanings = tuple(sorted({meaning for _, _, meaning in observations}))

        if len(independent) < 2:
            return LanguageVerificationResult(
                LanguageVerificationStatus.INSUFFICIENT,
                normalized_query,
                source_refs,
                independent,
                meanings,
                "Fewer than two independent language sources supplied usable observations.",
            )

        shared = set.intersection(*(values for values in by_source.values()))
        if shared:
            return LanguageVerificationResult(
                LanguageVerificationStatus.CORROBORATED,
                normalized_query,
                source_refs,
                independent,
                tuple(sorted(shared)),
                "At least two independent language sources report the same lexical meaning.",
            )

        return LanguageVerificationResult(
            LanguageVerificationStatus.DIVERGENT,
            normalized_query,
            source_refs,
            independent,
            meanings,
            "Independent language sources provide different lexical observations; no contradiction is inferred.",
        )

    @staticmethod
    def _source_identity(provider: str, item: LanguageEvidence) -> str:
        """Use the provider's explicit identity, never URL diversity, for independence."""
        identity = " ".join(str(provider).split()).casefold()
        return identity

    @staticmethod
    def _normalize_meaning(value: str) -> str:
        return " ".join(str(value).split()).casefold()


__all__ = [
    "LanguageEvidenceVerifier",
    "LanguageVerificationResult",
    "LanguageVerificationStatus",
]
