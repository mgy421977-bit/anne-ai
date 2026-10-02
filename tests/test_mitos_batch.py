"""Tests for the deterministic M7 batch-size protocol."""

from __future__ import annotations

from benchmarks.scripts.run_mitos_batch import run


def test_m7_protocol_reports_all_batch_conditions() -> None:
    result = run()
    assert [row["condition"] for row in result["results"]] == [
        "baseline",
        "small",
        "large",
    ]


def test_m7_protocol_is_deterministic_and_large_batch_finds_more_fixture_discovery() -> None:
    result = run()
    baseline, small, large = result["results"]

    assert baseline["discovery_hits_at_k"] == 0
    assert small["discovery_hits_at_k"] == 1
    assert large["discovery_hits_at_k"] == 2
    assert small["discovery_lift_vs_baseline"] == 1
    assert large["discovery_lift_vs_baseline"] == 2
