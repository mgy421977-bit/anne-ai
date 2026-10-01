"""Regression contract for the deterministic learning/research handoff benchmark."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks" / "scripts" / "run_learning_research_handoff.py"


def test_learning_research_handoff_benchmark_passes() -> None:
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
    assert payload["n"] == 7
    assert payload["mismatches"] == []
