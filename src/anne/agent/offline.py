"""Factory for running ANNE without external APIs or GitHub."""

from __future__ import annotations

from pathlib import Path

from anne.agent.runtime import AnneAgent
from anne.core.verification import ClaimVerifier
from anne.memory.local_memory import LocalMemory
from anne.providers.local import LocalProvider


def create_offline_agent(
    model: str | None = None,
    backend: str | None = None,
    endpoint: str | None = None,
    db_path: str | Path = "anne_offline.db",
    workspace: str | Path | None = None,
    *,
    response_verifier: ClaimVerifier | None = None,
    require_verified_response: bool = False,
) -> AnneAgent:
    """Create an agent backed only by a local model and SQLite."""
    return AnneAgent(
        model=LocalProvider(model=model, backend=backend, endpoint=endpoint),
        memory=LocalMemory(db_path),
        workspace=workspace,
        response_verifier=response_verifier,
        require_verified_response=require_verified_response,
    )


__all__ = ["create_offline_agent"]