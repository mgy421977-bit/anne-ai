"""Run an offline paired replay: PYTHONPATH=src python benchmarks/scripts/run_paired_replay.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

from anne.benchmarking import evaluate_replay


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/paired_replay_demo.json"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/paired_replay.json"))
    args = parser.parse_args()
    result = evaluate_replay(json.loads(args.dataset.read_text(encoding="utf-8")))
    source_root = Path(__file__).resolve().parents[2] / "src"
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        digest.update(path.relative_to(source_root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    result.update(
        timestamp=datetime.now(UTC).isoformat(), python=platform.python_version(),
        source_sha256=digest.hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"raw": result["raw"], "anne": result["anne"]}, indent=2))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())