"""Tests for the MITOS learning replay benchmark contract."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.scripts.run_mitos_learning import run


def test_mitos_learning_replay_fixture_passes() -> None:
    result = run()
    assert result["failed"] == 0
    assert result["passed"] == result["case_count"]


def test_fixture_declares_non_claim() -> None:
    fixture = json.loads(
        (Path(__file__).parents[1] / "benchmarks" / "mitos_learning_v01.json").read_text(
            encoding="utf-8"
        )
    )
    assert fixture["schema_version"] == "mitos_learning_v01"
