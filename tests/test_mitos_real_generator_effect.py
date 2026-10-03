"""Regression tests for the real MITOS generator guidance benchmark."""
from __future__ import annotations

from benchmarks.scripts.run_mitos_real_generator_effect import run


def test_real_generator_guidance_changes_mode_order() -> None:
    result = run()
    assert result["mode_order_changed"] is True
    assert result["baseline"]["modes"] != result["guided"]["modes"]


def test_real_generator_guidance_changes_downstream_characteristics() -> None:
    result = run()
    assert result["baseline"]["candidate_count"] == 12
    assert result["guided"]["candidate_count"] == 12
    assert result["discovery_value_delta"] != 0.0
