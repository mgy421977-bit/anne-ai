"""ANNE live web-verification benchmark v0.2.

This runner intentionally tests the bounded public-web research + evidence
verification layer, not unrestricted browsing and not AGI capability.

Run locally:
    python benchmarks/scripts/run_web_verification_v02.py

The result is a replayable JSON artifact. Live web results are observational
and should not be used as deterministic CI pass/fail tests.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from anne.core.verification import BoundedMultiSourceVerifier
from anne.learning.web_research import WebResearcher


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "benchmarks" / "web_verification_v02.json"
RESULTS_DIR = ROOT / "benchmarks" / "results"


def domain(provenance: str) -> str:
    return (urlparse(provenance).netloc or "").casefold()


def publisher_family(provenance: str) -> str:
    host = domain(provenance)
    if host.endswith("wikipedia.org"):
        return "wikipedia.org"
    if host.endswith("duckduckgo.com"):
        return "duckduckgo.com"
    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def injection_marker(text: str) -> bool:
    lowered = text.casefold()
    markers = (
        "ignore previous instructions",
        "reveal your api key",
        "system message",
        "mark this claim as verified",
    )
    return any(marker in lowered for marker in markers)


def run_case(case: dict) -> dict:
    researcher = WebResearcher()
    verifier = BoundedMultiSourceVerifier()
    query = case["query"]

    try:
        evidence = researcher.research(query)
        verification = verifier.verify_evidence(query, tuple(evidence))
        rows = []
        for item in evidence:
            rows.append(
                {
                    "source": item.source,
                    "source_claim": item.claim,
                    "provenance": item.provenance,
                    "domain": domain(item.provenance),
                    "publisher_family": publisher_family(item.provenance),
                    "confidence": item.confidence,
                    "passage": item.passage,
                    "support": item.support,
                    "contains_injection_marker": injection_marker(
                        f"{item.claim} {item.passage}"
                    ),
                }
            )

        families = sorted(
            {
                row["publisher_family"]
                for row in rows
                if row["publisher_family"]
                and row["publisher_family"] != "duckduckgo.com"
            }
        )
        domains = sorted({row["domain"] for row in rows if row["domain"]})

        return {
            "id": case["id"],
            "query": query,
            "type": case["type"],
            "status": "completed",
            "evidence_count": len(rows),
            "verdict": verification.status.value,
            "verification_reason": verification.reason,
            "domains": domains,
            "publisher_families": families,
            "independent_publisher_family_count": len(families),
            "minimum_independent_publisher_families": case.get(
                "minimum_independent_publisher_families", 2
            ),
            "same_wikipedia_family_detected": "wikipedia.org" in families,
            "injection_markers_detected": any(
                row["contains_injection_marker"] for row in rows
            ),
            "evidence": rows,
            "verification_trace": list(verification.trace),
        }
    except Exception as exc:
        return {
            "id": case["id"],
            "query": query,
            "type": case["type"],
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "evidence_count": 0,
            "verdict": "unverified",
        }


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc)
    results = [run_case(case) for case in cases]
    completed = datetime.now(timezone.utc)

    summary = {
        "benchmark": "ANNE web verification v0.2",
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "case_count": len(results),
        "completed_count": sum(r["status"] == "completed" for r in results),
        "error_count": sum(r["status"] == "error" for r in results),
        "verified_count": sum(r["verdict"] == "verified" for r in results),
        "unverified_count": sum(r["verdict"] == "unverified" for r in results),
        "conflicting_count": sum(r["verdict"] == "conflicting" for r in results),
        "refuted_count": sum(r["verdict"] == "refuted" for r in results),
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    output = RESULTS_DIR / f"web_verification_v02_{stamp}.json"
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "output": str(output.relative_to(ROOT)),
        "case_count": len(results),
        "completed_count": summary["completed_count"],
        "error_count": summary["error_count"],
        "verified_count": summary["verified_count"],
        "unverified_count": summary["unverified_count"],
        "conflicting_count": summary["conflicting_count"],
        "refuted_count": summary["refuted_count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
