"""Persistence tests for bounded learning observations."""

from pathlib import Path

from anne.memory.fractal_memory import FractalMemory


def test_experience_observation_round_trips_exact_context(tmp_path: Path) -> None:
    db = tmp_path / "anne.db"
    memory = FractalMemory(str(db))
    memory.save_experience_observation(
        source_cycle_id="cycle-1",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("freshness", "current"), ("source_count", "2")),
        parent_cycle_id=None,
        lineage=("cycle-1",),
    )

    reopened = FractalMemory(str(db))
    rows = reopened.get_experience_observations(
        context_key="web_research",
        context_conditions=(("freshness", "current"), ("source_count", "2")),
    )

    assert len(rows) == 1
    assert rows[0]["source_cycle_id"] == "cycle-1"
    assert rows[0]["safe_to_reuse"] is False
    assert rows[0]["context_key"] == "web_research"
    assert rows[0]["context_conditions"] == (
        ("freshness", "current"),
        ("source_count", "2"),
    )


def test_experience_observation_does_not_cross_context(tmp_path: Path) -> None:
    memory = FractalMemory(str(tmp_path / "anne.db"))
    memory.save_experience_observation(
        source_cycle_id="cycle-2",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="observation only",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
        context_key="web_research",
        context_conditions=(("freshness", "current"),),
    )

    rows = memory.get_experience_observations(
        context_key="local_research",
        context_conditions=(("freshness", "current"),),
    )

    assert rows == []
