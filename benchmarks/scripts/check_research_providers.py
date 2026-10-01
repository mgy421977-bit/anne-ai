#!/usr/bin/env python3
"""Diagnose ANNE's external research-provider readiness.

This is a local/runtime diagnostic, not a claim that the providers are live.
It reports configuration/dependency readiness and, when configured, performs
one bounded synthetic probe through each provider adapter.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import asdict, dataclass

from anne.learning.web_providers import (
    AgentReachProvider,
    PatchrightEnhancedProvider,
    ProviderLimits,
    ScraplingProvider,
)


@dataclass(frozen=True)
class ProviderCheck:
    name: str
    configured: bool
    dependency_ready: bool
    probe_attempted: bool
    probe_succeeded: bool
    evidence_count: int
    note: str


def _command_ready(env_var: str) -> bool:
    return bool(os.environ.get(env_var, "").strip())


def check_agent_reach() -> ProviderCheck:
    configured = _command_ready("ANNE_AGENT_REACH_COMMAND")
    provider = AgentReachProvider(limits=ProviderLimits(max_items=2, timeout_seconds=5))
    if not configured:
        return ProviderCheck(
            "agent-reach", False, True, False, False, 0,
            "ANNE_AGENT_REACH_COMMAND is not configured; fail-closed.",
        )
    items = provider.research("ANNE provider smoke test")
    return ProviderCheck(
        "agent-reach", True, True, True, bool(items), len(items),
        "Synthetic probe completed." if items else "Configured command returned no valid evidence.",
    )


def check_patchright() -> ProviderCheck:
    configured = _command_ready("ANNE_PATCHRIGHT_COMMAND")
    provider = PatchrightEnhancedProvider(
        limits=ProviderLimits(max_items=2, timeout_seconds=5)
    )
    if not configured:
        return ProviderCheck(
            "patchright-enhanced", False, True, False, False, 0,
            "ANNE_PATCHRIGHT_COMMAND is not configured; fail-closed.",
        )
    items = provider.research("ANNE provider smoke test")
    return ProviderCheck(
        "patchright-enhanced", True, True, True, bool(items), len(items),
        "Synthetic probe completed." if items else "Configured command returned no valid evidence.",
    )


def check_scrapling() -> ProviderCheck:
    enabled = os.environ.get("ANNE_SCRAPLING_ENABLED", "").lower() in {
        "1", "true", "yes"
    }
    dependency_ready = importlib.util.find_spec("scrapling") is not None
    if not enabled:
        return ProviderCheck(
            "scrapling", False, dependency_ready, False, False, 0,
            "ANNE_SCRAPLING_ENABLED is not enabled; provider is dormant.",
        )
    if not dependency_ready:
        return ProviderCheck(
            "scrapling", True, False, False, False, 0,
            "Scrapling package is not installed.",
        )

    def fake_fetch(url: str, **_: object) -> object:
        class Page:
            status = 200

            @staticmethod
            def get_all_text(**__: object) -> str:
                return "ANNE provider smoke test evidence."

        return Page()

    provider = ScraplingProvider(
        limits=ProviderLimits(max_items=2, timeout_seconds=5),
        fetch_page=fake_fetch,
    )
    items = provider.research("https://example.com/anne-smoke-test")
    return ProviderCheck(
        "scrapling", True, True, True, bool(items), len(items),
        "Adapter probe completed with a deterministic fetch fixture.",
    )


def main() -> int:
    checks = [
        check_agent_reach(),
        check_patchright(),
        check_scrapling(),
    ]
    print(json.dumps([asdict(item) for item in checks], ensure_ascii=False, indent=2))
    live_failures = [
        item for item in checks
        if item.probe_attempted and not item.probe_succeeded
    ]
    return 1 if live_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
