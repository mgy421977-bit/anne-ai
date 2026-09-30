"""Bounded orchestration for independent language corroboration."""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.intent import IntentFrame
from anne.language.evidence import LanguageEvidenceProvider, LanguageLookupResult
from anne.language.policy import LanguageCheckDecision, TurkishLanguageCheckPolicy
from anne.language.verification import (
    LanguageEvidenceVerifier,
    LanguageVerificationResult,
)


@dataclass(frozen=True)
class LanguageCorroborationResult:
    """A lexical corroboration attempt with explicit routing metadata."""

    decision: LanguageCheckDecision
    lookups: tuple[LanguageLookupResult, ...] = ()
    verification: LanguageVerificationResult | None = None

    @property
    def available(self) -> bool:
        """Return whether at least one provider returned usable evidence."""
        return any(lookup.available for lookup in self.lookups)

    @property
    def corroborated(self) -> bool:
        return (
            self.verification is not None
            and self.verification.status.value == "corroborated"
        )


class TurkishLanguageCorroborationService:
    """Call explicitly supplied language providers and compare their observations."""

    def __init__(
        self,
        providers: tuple[LanguageEvidenceProvider, ...] = (),
        policy: TurkishLanguageCheckPolicy | None = None,
        verifier: LanguageEvidenceVerifier | None = None,
    ) -> None:
        self._providers = tuple(providers)
        self._policy = policy or TurkishLanguageCheckPolicy()
        self._verifier = verifier or LanguageEvidenceVerifier()

    def check(
        self,
        query: str,
        intent: IntentFrame,
    ) -> LanguageCorroborationResult:
        decision = self._policy.decide(intent)
        if not decision.should_lookup:
            return LanguageCorroborationResult(decision=decision)

        if len(self._providers) < 2:
            return LanguageCorroborationResult(
                decision=decision,
                verification=self._verifier.verify(query, ()),
            )

        lookups: list[LanguageLookupResult] = []
        for provider in self._providers:
            try:
                lookups.append(provider.lookup(query))
            except Exception as exc:
                lookups.append(
                    LanguageLookupResult(
                        provider=getattr(provider, "provider_name", "unknown"),
                        query=query,
                        warnings=(f"Language provider failed: {type(exc).__name__}",),
                    )
                )

        verification = self._verifier.verify(query, tuple(lookups))
        return LanguageCorroborationResult(
            decision=decision,
            lookups=tuple(lookups),
            verification=verification,
        )


__all__ = ["LanguageCorroborationResult", "TurkishLanguageCorroborationService"]
