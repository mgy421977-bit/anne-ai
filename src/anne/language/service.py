"""Bounded orchestration for optional Turkish language evidence checks.

The service routes an explicit intent through the language-check policy, calls
an injected provider only when the policy allows it, and converts observations
to the existing research evidence model. It never verifies or grants authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.intent import IntentFrame
from anne.language.evidence import LanguageEvidenceProvider, LanguageLookupResult
from anne.language.learning import to_evidence_items
from anne.language.policy import LanguageCheckDecision, TurkishLanguageCheckPolicy
from anne.learning.evidence import EvidenceItem


@dataclass(frozen=True)
class LanguageCheckResult:
    """Bounded outcome of one optional language-evidence check."""

    decision: LanguageCheckDecision
    lookup: LanguageLookupResult | None = None
    evidence: tuple[EvidenceItem, ...] = ()

    @property
    def available(self) -> bool:
        """Whether the provider returned at least one ledger observation."""
        return bool(self.evidence)


class TurkishLanguageEvidenceService:
    """Coordinate policy, provider lookup, and evidence-ledger conversion."""

    def __init__(
        self,
        provider: LanguageEvidenceProvider | None = None,
        policy: TurkishLanguageCheckPolicy | None = None,
    ) -> None:
        self._provider = provider
        self._policy = policy or TurkishLanguageCheckPolicy()

    def check(self, query: str, intent: IntentFrame) -> LanguageCheckResult:
        decision = self._policy.decide(intent)
        if not decision.should_lookup:
            return LanguageCheckResult(decision=decision)

        if self._provider is None:
            return LanguageCheckResult(
                decision=decision,
                lookup=LanguageLookupResult(
                    provider="unconfigured",
                    query=query,
                    warnings=("No language evidence provider configured.",),
                ),
            )

        lookup = self._provider.lookup(query)
        evidence = to_evidence_items(lookup)
        return LanguageCheckResult(
            decision=decision,
            lookup=lookup,
            evidence=evidence,
        )


__all__ = ["LanguageCheckResult", "TurkishLanguageEvidenceService"]
