"""CLI: python -m tools.anne_vita_agent --vita-root PATH --workspace PATH < task.json"""
from __future__ import annotations

import argparse
import json
import sys

from .runner import build_default_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded local ANNE + VITA MVP")
    parser.add_argument("--vita-root", required=True, help="Local checkout of the VITA-Engine repository")
    parser.add_argument("--workspace", required=True, help="Writable local workspace for ANNE memory")
    args = parser.parse_args()
    try:
        task = json.load(sys.stdin)
        agent = build_default_agent(args.vita_root, args.workspace)
        result = agent.run(task)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("status") == "COMPLETED" else 2
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
