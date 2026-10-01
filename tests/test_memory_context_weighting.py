from __future__ import annotations

from anne.memory.context_weighting import weight_historical_decisions


def _row(
    verdict: str,
    topic: str,
    created_at: str,
    task_mode: str = "general",
) -> tuple[object, ...]:
    return (verdict, 0.8, "historical reasoning", topic, created_at, task_mode)


def test_newer_compatible_memory_outranks_older_memory() -> None:
    rows = [
        _row("OLD", "solar battery", "2026-09-01T10:00:00"),
        _row("NEW", "solar battery", "2026-10-01T10:00:00"),
    ]

    ranked = weight_historical_decisions(
        rows,
        topic="solar battery",
        now=None,
    )

    assert ranked[0].verdict == "NEW"
    assert ranked[0].weight > ranked[1].weight
    assert ranked[1].superseded is True
    assert ranked[0].superseded is False


def test_unrelated_context_is_excluded() -> None:
    rows = [
        _row("MATCH", "solar battery", "2026-10-01T10:00:00"),
        _row("UNRELATED", "olive oil", "2026-10-01T11:00:00"),
        _row("OTHER_MODE", "solar battery", "2026-10-01T12:00:00", "research"),
    ]

    ranked = weight_historical_decisions(
        rows,
        topic="solar battery",
        task_mode="general",
    )

    assert [item.verdict for item in ranked] == ["MATCH"]


def test_conflicting_historical_memory_is_surfaced_not_collapsed() -> None:
    rows = [
        _row("ACCEPT", "solar battery", "2026-10-01T10:00:00"),
        _row("REVIEW", "solar battery", "2026-10-01T11:00:00"),
    ]

    ranked = weight_historical_decisions(rows, topic="solar battery")

    assert len(ranked) == 2
    assert {item.verdict for item in ranked} == {"ACCEPT", "REVIEW"}
    assert all(
        item.conflict_group == "contradictory_historical_decisions"
        for item in ranked
    )


def test_memory_never_becomes_verification_or_authority() -> None:
    rows = [
        _row("VERIFIED", "a factual claim", "2026-10-01T10:00:00"),
    ]

    ranked = weight_historical_decisions(rows, topic="a factual claim")

    payload = ranked[0].as_dict()
    assert payload["status"] == "historical_context"
    assert payload["used_for_authority"] is False
    assert payload["used_for_fact_verification"] is False
    assert payload["status"] != "verified"
