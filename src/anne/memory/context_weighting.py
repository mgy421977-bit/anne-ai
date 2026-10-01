"""Bounded weighting for historical decision memory.

Historical memory is contextual evidence only. It never becomes verification,
authority, or a replacement for fresh evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MemoryContextCandidate:
    """Inspectable historical-memory candidate with bounded influence."""

    verdict: str
    total: float
    reasoning: str
    topic: str
    created_at: str
    relevance: float
    recency: float
    compatibility: float
    weight: float
    status: str
    superseded: bool = False
    conflict_group: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "total": self.total,
            "reasoning": self.reasoning,
            "topic": self.topic,
            "created_at": self.created_at,
            "relevance": self.relevance,
            "recency": self.recency,
            "compatibility": self.compatibility,
            "weight": self.weight,
            "status": self.status,
            "superseded": self.superseded,
            "conflict_group": self.conflict_group,
            "used_for_authority": False,
            "used_for_fact_verification": False,
        }


def _safe_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.min


def weight_historical_decisions(
    rows: list[tuple[Any, ...]],
    *,
    topic: str,
    task_mode: str = "general",
    now: datetime | None = None,
    limit: int = 5,
) -> list[MemoryContextCandidate]:
    """Rank historical decisions without collapsing contradictions.

    Row shape:
    verdict, total, reasoning, topic, created_at, task_mode.
    Exact task-mode compatibility is required; topic overlap supplies relevance.
    Older exact-topic decisions remain in history but are marked superseded when
    a newer compatible decision exists.
    """
    now = now or datetime.now()
    query_terms = {
        token.casefold()
        for token in topic.split()
        if token.strip()
    }
    scored: list[MemoryContextCandidate] = []

    for row in rows:
        if len(row) < 6:
            continue
        verdict, total, reasoning, memory_topic, created_at, memory_mode = row[:6]
        if memory_mode != task_mode:
            continue
        memory_terms = {
            token.casefold()
            for token in str(memory_topic).split()
            if token.strip()
        }
        overlap = len(query_terms & memory_terms)
        relevance = overlap / max(1, len(query_terms))
        if relevance <= 0:
            continue
        created = _safe_datetime(str(created_at))
        age_days = max(0.0, (now - created).total_seconds() / 86400.0)
        recency = 1.0 / (1.0 + age_days / 30.0)
        compatibility = 1.0
        weight = round((0.55 * relevance) + (0.25 * recency) + (0.20 * compatibility), 6)
        scored.append(
            MemoryContextCandidate(
                verdict=str(verdict),
                total=float(total),
                reasoning=str(reasoning),
                topic=str(memory_topic),
                created_at=str(created_at),
                relevance=round(relevance, 6),
                recency=round(recency, 6),
                compatibility=compatibility,
                weight=weight,
                status="historical_context",
            )
        )

    scored.sort(key=lambda item: (item.weight, item.created_at), reverse=True)

    latest_by_topic: dict[str, str] = {}
    for item in scored:
        key = item.topic.casefold()
        latest_by_topic.setdefault(key, item.created_at)

    superseded: list[MemoryContextCandidate] = []
    for item in scored:
        is_superseded = item.created_at < latest_by_topic[item.topic.casefold()]
        superseded.append(
            replace(item, superseded=is_superseded)
        )

    verdicts = {item.verdict for item in superseded if not item.superseded}
    conflict = len(verdicts) > 1
    conflict_group = "contradictory_historical_decisions" if conflict else ""
    final = [
        replace(item, conflict_group=conflict_group)
        for item in superseded
    ]
    return final[:limit]


__all__ = ["MemoryContextCandidate", "weight_historical_decisions"]
