"""Bounded external research providers for ANNE.

The providers in this module are retrieval adapters only. They produce
non-authoritative EvidenceItem records and never verify claims, grant
authority, or execute user actions.

External tools are optional:
- Agent Reach is treated as a capability/router layer and is invoked only
  through an explicitly configured command adapter.
- Scrapling is used directly when its optional dependency is installed.
- Patchright Enhanced is treated as an external browser adapter and is
  invoked only through an explicitly configured command adapter.

All adapters fail closed and enforce bounded output.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse

from anne.learning.evidence import EvidenceItem


class ExternalResearchProvider(Protocol):
    """Retrieval-only provider contract."""

    name: str

    def research(self, query: str) -> Sequence[EvidenceItem]:
        ...


@dataclass(frozen=True)
class ProviderLimits:
    """Hard bounds applied before data enters ANNE's evidence layer."""

    max_items: int = 8
    max_claim_chars: int = 2200
    max_passage_chars: int = 1200
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if self.max_items < 1:
            raise ValueError("max_items must be positive")
        if self.max_claim_chars < 1 or self.max_passage_chars < 1:
            raise ValueError("text limits must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _evidence(
    *,
    provider: str,
    source: str,
    claim: str,
    provenance: str,
    passage: str = "",
    confidence: float = 0.50,
    kind: str = "web_external",
) -> EvidenceItem:
    return EvidenceItem(
        source=source,
        claim=claim[:2200],
        kind=kind,
        provenance=provenance,
        confidence=max(0.0, min(1.0, confidence)),
        passage=passage[:1200],
        retrieved_at=_now(),
    )


class CommandResearchProvider:
    """Safe adapter for an externally installed research CLI.

    The command must return JSON Lines. Each line may contain:
    {"claim": "...", "provenance": "...", "passage": "...",
     "source": "...", "confidence": 0.7}

    No shell is used. The command prefix is supplied as an argv sequence or
    through an environment variable containing a shell-like argv string.
    """

    def __init__(
        self,
        *,
        name: str,
        command: Sequence[str] | None = None,
        env_var: str | None = None,
        limits: ProviderLimits | None = None,
    ) -> None:
        self.name = name
        self.limits = limits or ProviderLimits()
        if command:
            self.command = tuple(command)
        elif env_var and os.environ.get(env_var):
            self.command = tuple(shlex.split(os.environ[env_var]))
        else:
            self.command = ()

    def research(self, query: str) -> Sequence[EvidenceItem]:
        if not query.strip() or not self.command:
            return ()
        try:
            completed = subprocess.run(
                [*self.command, query],
                capture_output=True,
                text=True,
                timeout=self.limits.timeout_seconds,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ()
        if completed.returncode != 0:
            return ()

        items: list[EvidenceItem] = []
        for line in completed.stdout.splitlines()[: self.limits.max_items]:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            claim = str(row.get("claim", "")).strip()
            provenance = str(row.get("provenance", "")).strip()
            if not claim or not provenance:
                continue
            source = str(row.get("source") or self.name).strip()
            passage = str(row.get("passage", "")).strip()
            try:
                confidence = float(row.get("confidence", 0.50))
            except (TypeError, ValueError):
                confidence = 0.50
            items.append(
                _evidence(
                    provider=self.name,
                    source=source,
                    claim=claim[: self.limits.max_claim_chars],
                    provenance=provenance,
                    passage=passage[: self.limits.max_passage_chars],
                    confidence=confidence,
                )
            )
        return tuple(items)


class AgentReachProvider(CommandResearchProvider):
    """Adapter for an explicitly configured Agent-Reach research command.

    Agent-Reach is a router/installer rather than ANNE's evidence authority.
    Configure ANNE_AGENT_REACH_COMMAND to point at a local wrapper that emits
    the JSONL contract above. This avoids relying on unstable agent-facing
    command names and keeps credentials outside ANNE's process arguments.
    """

    def __init__(self, *, limits: ProviderLimits | None = None) -> None:
        super().__init__(
            name="agent-reach",
            env_var="ANNE_AGENT_REACH_COMMAND",
            limits=limits,
        )


class PatchrightEnhancedProvider(CommandResearchProvider):
    """Adapter for an external Patchright Enhanced JSONL browser worker."""

    def __init__(self, *, limits: ProviderLimits | None = None) -> None:
        super().__init__(
            name="patchright-enhanced",
            env_var="ANNE_PATCHRIGHT_COMMAND",
            limits=limits,
        )


class ScraplingProvider:
    """Optional direct Scrapling retrieval adapter.

    This adapter intentionally supports a URL-shaped query only. It extracts
    bounded page text and records the URL as provenance. Claim verification is
    left to ANNE's existing evidence/verification layers.
    """

    name = "scrapling"

    def __init__(
        self,
        *,
        limits: ProviderLimits | None = None,
        fetch_page: Callable[..., object] | None = None,
    ) -> None:
        self.limits = limits or ProviderLimits()
        self._fetch_page = fetch_page

    def research(self, query: str) -> Sequence[EvidenceItem]:
        parsed = urlparse(query.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ()

        fetch_page = self._fetch_page
        if fetch_page is None:
            try:
                from scrapling.fetchers import Fetcher  # type: ignore[import-not-found]
            except ImportError:
                return ()
            fetch_page = Fetcher.get

        try:
            page = fetch_page(
                query,
                timeout=self.limits.timeout_seconds,
                retries=0,
                follow_redirects="safe",
            )
            status = getattr(page, "status", 200)
            if isinstance(status, int) and status >= 400:
                return ()
            if hasattr(page, "get_all_text"):
                text = str(page.get_all_text(ignore_tags=("script", "style")))
            else:
                text = str(getattr(page, "text", ""))
        except Exception:
            return ()

        text = " ".join(text.split())
        if not text:
            return ()

        passage = text[: self.limits.max_passage_chars]
        claim = text[: self.limits.max_claim_chars]
        return (
            _evidence(
                provider=self.name,
                source="Scrapling fetched page",
                claim=claim,
                provenance=query,
                passage=passage,
                confidence=0.50,
            ),
        )


class ResearchProviderRegistry:
    """Bounded provider fan-out with deterministic de-duplication."""

    def __init__(
        self,
        providers: Sequence[ExternalResearchProvider] = (),
        *,
        max_total_items: int = 12,
    ) -> None:
        if max_total_items < 1:
            raise ValueError("max_total_items must be positive")
        self.providers = tuple(providers)
        self.max_total_items = max_total_items

    def research(self, query: str) -> tuple[EvidenceItem, ...]:
        if not query.strip():
            return ()
        result: list[EvidenceItem] = []
        seen: set[tuple[str, str]] = set()
        for provider in self.providers:
            try:
                items = provider.research(query)
            except Exception:
                continue
            for item in items:
                key = (item.provenance.strip(), item.claim.strip())
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                result.append(item)
                if len(result) >= self.max_total_items:
                    return tuple(result)
        return tuple(result)


def default_external_registry() -> ResearchProviderRegistry:
    """Build only explicitly enabled external providers.

    No external tool is executed merely by importing ANNE.
    """
    providers: list[ExternalResearchProvider] = []
    if os.environ.get("ANNE_AGENT_REACH_COMMAND"):
        providers.append(AgentReachProvider())
    if os.environ.get("ANNE_PATCHRIGHT_COMMAND"):
        providers.append(PatchrightEnhancedProvider())
    if os.environ.get("ANNE_SCRAPLING_ENABLED", "").lower() in {"1", "true", "yes"}:
        providers.append(ScraplingProvider())
    return ResearchProviderRegistry(providers)


__all__ = [
    "AgentReachProvider",
    "CommandResearchProvider",
    "ExternalResearchProvider",
    "PatchrightEnhancedProvider",
    "ProviderLimits",
    "ResearchProviderRegistry",
    "ScraplingProvider",
    "default_external_registry",
]
