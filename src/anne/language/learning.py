"""Bridge language-provider observations into ANNE's research evidence model.

The bridge preserves the non-authoritative status of language observations.
It does not verify, rank, or promote them to factual truth.
"""

from __future__ import annotations

from anne.language.evidence import LanguageLookupResult
from anne.learning.evidence import EvidenceItem, SupportStatus


def to_evidence_items(result: LanguageLookupResult) -> tuple[EvidenceItem, ...]:
    """Convert a bounded language lookup into ledger-compatible observations."""
    items: list[EvidenceItem] = []
    for index, item in enumerate(result.evidence):
        passage = item.meaning
        if item.examples:
            passage += " Examples: " + " | ".join(item.examples)
        if item.context:
            context = "; ".join(f"{key}={value}" for key, value in item.context)
            passage += f" Context: {context}"

        items.append(
            EvidenceItem(
                source=result.provider,
                claim=item.meaning,
                kind="language",
                provenance=item.source_ref,
                confidence=0.5,
                passage=passage,
                support=SupportStatus.UNCLEAR.value,
            )
        )
    return tuple(items)


__all__ = ["to_evidence_items"]
