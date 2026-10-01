"""Regression contract for the deterministic MITOS strategy-learning benchmark."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks" / "scripts" / "run_mitos_strategy_learning.py"


def test_mitos_strategy_learning_benchmark_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["n"] == 2
    assert payload["mismatches"] == []
