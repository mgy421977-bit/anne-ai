"""Provider-neutral language evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from anne.semantics.core import Evidence, Provenance


@dataclass(frozen=True)
class LanguageEvidence:
    """One provenance-bearing observation about a word or expression."""

    query: str
    meaning: str
    source_ref: str
    source_type: str = "tool"
    examples: tuple[str, ...] = ()
    context: tuple[tuple[str, str], ...] = ()
    content_hash: str = ""

    def as_evidence(self, evidence_id: str) -> Evidence:
        content = self.meaning
        if self.examples:
            content = f"{content} Examples: " + " | ".join(self.examples)
        provenance = Provenance(
            source_type=self.source_type,
            source_ref=self.source_ref,
            content_hash=self.content_hash,
            verified=False,
        )
        return Evidence(
            id=evidence_id,
            content=content,
            provenance=provenance,
            confidence=0.5,
        )


@dataclass(frozen=True)
class LanguageLookupResult:
    """A bounded lookup result; empty results are valid and non-failing."""

    provider: str
    query: str
    evidence: tuple[LanguageEvidence, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return bool(self.evidence)


@runtime_checkable
class LanguageEvidenceProvider(Protocol):
    """Contract for external language/lexicographic evidence."""

    provider_name: str

    def lookup(self, query: str) -> LanguageLookupResult:
        """Return provenance-bearing language observations for query."""
        ...


__all__ = ["LanguageEvidence", "LanguageEvidenceProvider", "LanguageLookupResult"]
