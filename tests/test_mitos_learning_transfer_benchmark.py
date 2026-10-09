"""Tests for the reproducible MITOS learning transfer benchmark."""

from __future__ import annotations

from benchmarks.scripts.run_mitos_learning_transfer import run_benchmark


def test_learning_transfer_changes_generation_order_and_isolates_context() -> None:
    result = run_benchmark()

    assert result["matched_experiences"] == 3
    assert result["ordering_changed"] is True
    assert result["preferred_modes"] == ["COMBINE"]
    assert result["avoid_modes"] == ["INVERT"]
    assert result["cross_context_isolated"] is True
    assert result["execution_authority"] is False
