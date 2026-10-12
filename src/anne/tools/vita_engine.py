"""Optional ANNE tool bridge to the VITA-Engine deterministic core.

Set VITA_ENGINE_PATH to a trusted local checkout of VITA-Engine. This bridge
never downloads or executes remote code and never exposes a network endpoint.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any


class VitaEngineTool:
    """Call the allow-listed in-process VITA adapter from an ANNE host process."""

    name = "vita_engine_assess"
    description = (
        "Run a deterministic VITA-Engine carbon assessment, preliminary Türkiye ETS "
        "precheck, or EU/Türkiye taxonomy checklist. Always requires human review."
    )

    def __init__(self, engine_path: str | Path | None = None) -> None:
        configured = engine_path or os.environ.get("VITA_ENGINE_PATH")
        if not configured:
            raise RuntimeError(
                "VITA_ENGINE_PATH must point to a trusted local VITA-Engine checkout."
            )
        self.root = Path(configured).expanduser().resolve()
        if not (self.root / "api" / "anne_adapter.py").is_file():
            raise FileNotFoundError(
                f"VITA-Engine adapter not found under configured path: {self.root}"
            )

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute one allow-listed request and return its structured result."""
        if not isinstance(request, dict):
            raise ValueError("VITA request must be a JSON-like object")
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        adapter = importlib.import_module("api.anne_adapter")
        handler = getattr(adapter, "handle_anne_request", None)
        if not callable(handler):
            raise RuntimeError("Configured VITA adapter has no callable request handler")
        result = handler(request)
        if not isinstance(result, dict):
            raise RuntimeError("VITA adapter returned a non-object response")
        return {str(key): value for key, value in result.items()}


__all__ = ["VitaEngineTool"]
