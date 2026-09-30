"""TDK language-evidence adapter.

The public TDK dictionary is not treated as a stable API here. The adapter
accepts an injected resolver so ANNE can use an approved access mechanism
without coupling the cognitive core to scraping or undocumented endpoints.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import Any

from anne.language.evidence import LanguageEvidence, LanguageLookupResult

Resolver = Callable[[str], Mapping[str, Any] | None]


class TdkProvider:
    """Convert an approved TDK lookup into non-authoritative evidence."""

    provider_name = "tdk"

    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolver = resolver

    def lookup(self, query: str) -> LanguageLookupResult:
        normalized = " ".join(str(query).split())
        if not normalized:
            return LanguageLookupResult(self.provider_name, normalized)

        if self._resolver is None:
            return LanguageLookupResult(
                self.provider_name,
                normalized,
                warnings=("No approved TDK resolver configured.",),
            )

        try:
            payload = self._resolver(normalized)
        except Exception as exc:
            return LanguageLookupResult(
                self.provider_name,
                normalized,
                warnings=(f"TDK resolver failed: {type(exc).__name__}",),
            )

        if not isinstance(payload, Mapping):
            return LanguageLookupResult(
                self.provider_name,
                normalized,
                warnings=("TDK resolver returned no structured result.",),
            )

        meaning = str(payload.get("meaning") or "").strip()
        if not meaning:
            return LanguageLookupResult(
                self.provider_name,
                normalized,
                warnings=("TDK result contains no lexical meaning.",),
            )

        source_ref = str(payload.get("source_ref") or "").strip()
        if not source_ref:
            return LanguageLookupResult(
                self.provider_name,
                normalized,
                warnings=("TDK result has no explicit source provenance.",),
            )

        examples = tuple(
            str(item).strip()
            for item in payload.get("examples", ())
            if str(item).strip()
        )
        context_items = payload.get("context", {})
        context = (
            tuple(sorted((str(key), str(value)) for key, value in context_items.items()))
            if isinstance(context_items, Mapping)
            else ()
        )

        digest_input = meaning + "\n" + "\n".join(examples)
        content_hash = sha256(digest_input.encode("utf-8")).hexdigest()

        evidence = LanguageEvidence(
            query=normalized,
            meaning=meaning,
            source_ref=source_ref,
            source_type="official_dictionary",
            examples=examples,
            context=context,
            content_hash=content_hash,
        )
        return LanguageLookupResult(
            self.provider_name,
            normalized,
            evidence=(evidence,),
        )


__all__ = ["TdkProvider"]
