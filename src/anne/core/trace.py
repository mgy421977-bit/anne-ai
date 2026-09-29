"""Versioned, provider-independent canonical cognitive cycle trace."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

TRACE_SCHEMA_VERSION = "1.2"


@dataclass(frozen=True)
class CycleTrace:
    """Canonical inspectable record for one bounded ANNE cognitive cycle."""

    cycle_id: str
    status: str
    stage_trace: tuple[str, ...] = ()
    schema_version: str = TRACE_SCHEMA_VERSION
    parent_cycle_id: str | None = None
    stop_reason: str = ""
    retry_count: int = 0
    lineage: tuple[str, ...] = ()
    intent: Mapping[str, Any] = field(default_factory=dict)
    hypotheses: tuple[Mapping[str, Any], ...] = ()
    evidence: tuple[Mapping[str, Any], ...] = ()
    joint_inferences: tuple[Mapping[str, Any], ...] = ()
    derived_hypotheses: tuple[Mapping[str, Any], ...] = ()
    re_evaluation: Mapping[str, Any] = field(default_factory=dict)
    verification: Mapping[str, Any] = field(default_factory=dict)
    decision: Mapping[str, Any] = field(default_factory=dict)
    agency: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    learning: Mapping[str, Any] = field(default_factory=dict)
    metrics: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.cycle_id.strip():
            raise ValueError("cycle_id must not be empty")
        if not self.status.strip():
            raise ValueError("status must not be empty")
        if not self.schema_version.strip():
            raise ValueError("schema_version must not be empty")
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if self.parent_cycle_id == self.cycle_id:
            raise ValueError("parent_cycle_id must differ from cycle_id")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CycleTrace:
        data = dict(payload)
        for key in (
            "stage_trace",
            "lineage",
            "hypotheses",
            "evidence",
            "joint_inferences",
            "derived_hypotheses",
            "errors",
        ):
            data[key] = tuple(data.get(key, ()))
        return cls(**data)


def trace_from_runtime(
    *,
    cycle_id: str,
    status: str,
    stage_trace: tuple[str, ...],
    stop_reason: str,
    retry_count: int,
    lineage: tuple[str, ...],
    output: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    learning_context: Mapping[str, Any] | None = None,
) -> CycleTrace:
    """Copy explicit runtime observations without inferring truth or authority."""
    output = dict(output or {})
    context = dict(context or {})
    verification: dict[str, Any] = {
        key: context[key]
        for key in (
            "verification_status",
            "verification_sources",
            "verification_reason",
            "evidence_status",
            "evidence_verified",
        )
        if key in context
    }
    decision: dict[str, Any] = {
        key: output[key]
        for key in ("verdict", "action", "reason", "factual_status")
        if key in output
    }
    agency: dict[str, Any] = {
        key: output[key]
        for key in ("agency_decision", "agency_reason", "human_review_required")
        if key in output
    }
    intent: dict[str, Any] = {
        key: context[key]
        for key in ("intent", "intent_confidence", "ambiguity", "requires_evidence")
        if key in context
    }
    learning: dict[str, Any] = {}
    if learning_context is not None:
        learning["context"] = dict(learning_context)
    return CycleTrace(
        cycle_id=cycle_id,
        parent_cycle_id=lineage[-2] if len(lineage) > 1 else None,
        status=status,
        stage_trace=stage_trace,
        stop_reason=stop_reason,
        retry_count=retry_count,
        lineage=lineage,
        intent=intent,
        joint_inferences=tuple(context.get("joint_inferences", ())),
        derived_hypotheses=tuple(context.get("derived_hypotheses", ())),
        re_evaluation=dict(context.get("re_evaluation", {})),
        verification=verification,
        decision=decision,
        agency=agency,
        learning=learning,
    )


__all__ = ["TRACE_SCHEMA_VERSION", "CycleTrace", "trace_from_runtime"]
