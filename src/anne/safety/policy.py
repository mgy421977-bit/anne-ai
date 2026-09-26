"""Conservative local safety policies for tools and persistent memory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Bare tokens and labeled secrets. Replacements avoid forcing "prefix=[REDACTED]".
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Bearer <token>
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+=/]{8,}"), "Bearer [REDACTED]"),
    # OpenAI-style project keys
    (re.compile(r"\bsk-proj-[A-Za-z0-9_\-]{8,}\b"), "[REDACTED]"),
    # GitHub fine-grained PAT
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{8,}\b"), "[REDACTED]"),
    # Classic GitHub PAT / generic sk_ / ghp_
    (re.compile(r"\b(?:sk|ghp)_[A-Za-z0-9_\-]{12,}\b"), "[REDACTED]"),
    # key/token/password/secret = value (preserve key name, redact value only)
    (
        re.compile(
            r"(?i)((?:api[_ -]?key|token|password|secret)\s*[:=]\s*)([^\s,;]+)"
        ),
        r"\1[REDACTED]",
    ),
)


def redact_sensitive(text: str) -> str:
    """Redact common credentials before text enters durable memory."""
    redacted = text
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_data(value: Any) -> Any:
    """Redact text recursively without changing structured memory schemas."""
    if isinstance(value, str):
        return redact_sensitive(value)
    if isinstance(value, dict):
        return {redact_data(key): redact_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    return value


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    reason: str
    risk: float | None = None
    reversible: bool | None = None
    authority_required: bool | None = None
    evidence_required: bool | None = None
    side_effect: bool | None = None
    human_review_required: bool | None = None


@dataclass(frozen=True)
class ToolMetadata:
    """Explicit policy facts for one registered tool."""

    risk: float | None
    reversible: bool | None
    authority_required: bool | None
    evidence_required: bool | None
    side_effect: bool | None
    human_review_required: bool | None


class ToolPolicy:
    """Allowlist tool names and reject suspicious path arguments."""

    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        defaults = {
            "github_read_file",
            "github_list",
            "github_search",
            "local_list",
            "local_read",
        }
        self.allowed_tools = set(defaults if allowed_tools is None else allowed_tools)
        read_only = ToolMetadata(
            risk=0.10,
            reversible=True,
            authority_required=False,
            evidence_required=False,
            side_effect=False,
            human_review_required=False,
        )
        self.tool_metadata: dict[str, ToolMetadata] = {
            name: read_only for name in defaults
        }

    def authorize(self, name: str, arguments: dict[str, Any] | None = None) -> ToolDecision:
        if name not in self.allowed_tools:
            return ToolDecision(False, f"Tool is not allowlisted: {name}")
        for value in (arguments or {}).values():
            suspicious = ("../", "rm -rf", "delete")
            if isinstance(value, str) and any(
                token in value.lower() for token in suspicious
            ):
                return ToolDecision(False, "Suspicious tool argument blocked")
        metadata = self.tool_metadata.get(name, ToolMetadata(None, None, None, None, None, None))
        return ToolDecision(
            True,
            "allowlisted read operation",
            risk=metadata.risk,
            reversible=metadata.reversible,
            authority_required=metadata.authority_required,
            evidence_required=metadata.evidence_required,
            side_effect=metadata.side_effect,
            human_review_required=metadata.human_review_required,
        )


__all__ = [
    "ToolDecision",
    "ToolMetadata",
    "ToolPolicy",
    "redact_data",
    "redact_sensitive",
]
