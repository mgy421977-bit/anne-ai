"""Provider-independent canonical runtime entry for ANNE V1 Core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anne.core.cognitive_state import Consciousness
from anne.core.decision_loop import DecisionLoop, DecisionResult
from anne.core.verification import ClaimVerifier


@dataclass(frozen=True)
class AnneRequest:
    """Small client-neutral request contract for the guarded runtime."""

    text: str
    parties: tuple[Consciousness, ...] = ()


class AnneRuntime:
    """Canonical request → cognitive orchestrator → gated decision boundary."""

    def __init__(
        self,
        decision_loop: DecisionLoop | None = None,
        *,
        verifier: ClaimVerifier | None = None,
    ) -> None:
        self.decision_loop = decision_loop or DecisionLoop(claim_verifier=verifier)
        self.verifier = verifier

    def handle(self, request: AnneRequest) -> DecisionResult:
        text = request.text.strip()
        if not text:
            raise ValueError("request text is required")
        return self.run(text, parties=request.parties)

    def run(
        self,
        text: str,
        *,
        parties: tuple[Consciousness, ...] | None = None,
    ) -> DecisionResult:
        return self.decision_loop.run(
            text,
            parties=parties,
            verifier=self.verifier,
        )

    def run_cognitive(
        self,
        text: str,
        *,
        parties: tuple[Consciousness, ...] | None = None,
        seed: int | None = None,
    ) -> Any:
        """Expose the same canonical chain for clients needing the full trace."""
        return self.decision_loop.run_cognitive(
            text,
            parties=parties,
            seed=seed,
            verifier=self.verifier,
        )


__all__ = ["AnneRequest", "AnneRuntime"]
