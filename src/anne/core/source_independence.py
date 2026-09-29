"""Conservative source-family identity and independence assessment.

Publisher-family diversity is a structural signal, not proof of independent
evidence. Two URLs may reproduce the same underlying report, while an unknown
relationship must remain unknown rather than being upgraded to independent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class SourceIndependenceStatus(StrEnum):
    MULTIPLE_PUBLISHER_FAMILIES = "multiple_publisher_families"
    SINGLE_PUBLISHER_FAMILY = "single_publisher_family"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceIndependenceAssessment:
    """Bounded assessment of publisher-family diversity."""

    status: SourceIndependenceStatus
    publisher_families: tuple[str, ...] = ()
    unknown_sources: int = 0

    @property
    def distinct_publisher_family_count(self) -> int:
        return len(self.publisher_families)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "publisher_families": list(self.publisher_families),
            "unknown_sources": self.unknown_sources,
            "distinct_publisher_family_count": self.distinct_publisher_family_count,
        }


class SourceIndependence:
    """Conservative publisher-family classifier.

    URL uniqueness is deliberately not treated as evidence independence.
    A known family only establishes that the source belongs to that publisher
    family; it does not establish that the underlying reporting is independent.
    """

    _MULTI_LABEL_SUFFIXES = frozenset(
        {
            "co.uk",
            "org.uk",
            "ac.uk",
            "gov.uk",
            "com.au",
            "net.au",
            "org.au",
            "co.nz",
            "com.br",
            "com.tr",
            "co.jp",
            "co.kr",
            "com.cn",
            "com.mx",
            "com.ar",
            "co.za",
            "com.sg",
        }
    )

    _KNOWN_FAMILIES = {
        "wikipedia.org": "wikipedia.org",
        "duckduckgo.com": "duckduckgo.com",
    }

    @classmethod
    def publisher_family(cls, provenance: str) -> str:
        """Return a conservative publisher-family identity or an empty value."""
        if not isinstance(provenance, str) or not provenance.strip():
            return ""

        parsed = urlparse(provenance.strip())
        host = (parsed.hostname or "").casefold().rstrip(".")
        if not host:
            return ""

        for known_host, family in cls._KNOWN_FAMILIES.items():
            if host == known_host or host.endswith(f".{known_host}"):
                return family

        parts = [part for part in host.split(".") if part]
        if len(parts) < 2:
            return host

        suffix = ".".join(parts[-2:])
        if suffix in cls._MULTI_LABEL_SUFFIXES and len(parts) >= 3:
            return ".".join(parts[-3:])
        return suffix

    @classmethod
    def assess(cls, provenances: tuple[str, ...]) -> SourceIndependenceAssessment:
        families = sorted(
            {
                family
                for provenance in provenances
                if (family := cls.publisher_family(provenance))
            }
        )
        unknown_sources = sum(
            1 for provenance in provenances if not cls.publisher_family(provenance)
        )

        if unknown_sources:
            status = SourceIndependenceStatus.UNKNOWN
        elif len(families) >= 2:
            status = SourceIndependenceStatus.MULTIPLE_PUBLISHER_FAMILIES
        elif len(families) == 1:
            status = SourceIndependenceStatus.SINGLE_PUBLISHER_FAMILY
        else:
            status = SourceIndependenceStatus.UNKNOWN

        return SourceIndependenceAssessment(
            status=status,
            publisher_families=tuple(families),
            unknown_sources=unknown_sources,
        )


__all__ = ["SourceIndependence", "SourceIndependenceAssessment", "SourceIndependenceStatus"]
