"""Local-first, human-governed company workflow MVP for Vitavolt Global.

This module creates and tracks a sales-oriented task graph. It does not scrape
websites, contact prospects, send email, spend money, or execute external actions.
Those capabilities must be separately integrated behind ANNE's Agency Gate.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class WorkItem:
    id: str
    title: str
    purpose: str
    depends_on: tuple[str, ...]
    priority: int
    status: str = "pending"


@dataclass(frozen=True)
class ActionProposal:
    action: str
    reason: str
    scope: str
    evidence: tuple[str, ...]
    risk: str
    validation: str
    rollback: str
    status: str = "PENDING_APPROVAL"


VITAVOLT_AI_INFRASTRUCTURE_PLAN: tuple[WorkItem, ...] = (
    WorkItem("market_map", "Map AI infrastructure energy demand",
             "Define target segments: data centres, AI compute operators, colocation and industrial campuses.",
             (), 1),
    WorkItem("offer", "Define Vitavolt's offer",
             "Package PV, BESS, grid-interface, EMS and energy-resilience engineering without promising unverified performance.",
             ("market_map",), 1),
    WorkItem("qualification", "Create target-account qualification criteria",
             "Score accounts by location, power demand, project timing, procurement route and evidence quality.",
             ("market_map", "offer"), 2),
    WorkItem("evidence", "Build an evidence-backed prospect list",
             "Collect public company facts and source URLs; mark unknowns instead of guessing.",
             ("qualification",), 2),
    WorkItem("commercial", "Prepare a discovery and qualification pack",
             "Draft questions, technical discovery checklist and a first-meeting agenda.",
             ("offer", "qualification"), 2),
    WorkItem("case_model", "Prepare a transparent preliminary energy model",
             "Create assumptions-led PV/BESS sizing and economics; label estimates and require engineering review.",
             ("offer",), 3),
    WorkItem("outreach_draft", "Draft tailored outreach for review",
             "Prepare personalised drafts tied to verified account facts; do not send automatically.",
             ("evidence", "commercial"), 3),
    WorkItem("weekly_review", "Review pipeline and next actions",
             "Summarise completed work, blockers, evidence gaps and founder decisions required.",
             ("evidence", "commercial", "case_model"), 4),
)


class VitavoltCompanyEngine:
    """Persistent SQLite task graph with dependency checks and proposal-only agency."""

    def __init__(self, db_path: str | Path = ".anne/vitavolt_company_engine.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS work_items (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, purpose TEXT NOT NULL,
                depends_on TEXT NOT NULL, priority INTEGER NOT NULL,
                status TEXT NOT NULL, updated_at TEXT NOT NULL, result TEXT NOT NULL DEFAULT ''
            )"""
        )
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS action_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
                reason TEXT NOT NULL, scope TEXT NOT NULL, evidence TEXT NOT NULL,
                risk TEXT NOT NULL, validation TEXT NOT NULL, rollback TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL
            )"""
        )
        self._connection.commit()

    def seed_plan(self, items: Iterable[WorkItem] = VITAVOLT_AI_INFRASTRUCTURE_PLAN) -> None:
        """Insert the starter plan without overwriting existing progress."""
        now = datetime.now(UTC).isoformat()
        with self._connection:
            for item in items:
                self._connection.execute(
                    """INSERT OR IGNORE INTO work_items
                    (id,title,purpose,depends_on,priority,status,updated_at,result)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (item.id, item.title, item.purpose, json.dumps(item.depends_on),
                     item.priority, item.status, now, ""),
                )

    def list_work(self) -> list[dict[str, object]]:
        rows = self._connection.execute(
            "SELECT * FROM work_items ORDER BY priority, id"
        ).fetchall()
        return [{
            "id": row["id"], "title": row["title"], "purpose": row["purpose"],
            "depends_on": json.loads(row["depends_on"]), "priority": row["priority"],
            "status": row["status"], "updated_at": row["updated_at"], "result": row["result"],
        } for row in rows]

    def next_work(self, limit: int = 3) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        rows = self.list_work()
        completed = {str(row["id"]) for row in rows if row["status"] == "completed"}
        ready = [
            row for row in rows
            if row["status"] == "pending"
            and set(row["depends_on"]).issubset(completed)  # type: ignore[arg-type]
        ]
        return ready[:limit]

    def complete_work(self, item_id: str, result: str) -> None:
        """Record a work result only when its dependencies are complete."""
        if not result.strip():
            raise ValueError("result must not be empty")
        row = self._connection.execute(
            "SELECT * FROM work_items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown work item: {item_id}")
        if row["status"] == "completed":
            raise ValueError(f"work item already completed: {item_id}")
        dependencies = set(json.loads(row["depends_on"]))
        completed = {
            r["id"] for r in self._connection.execute(
                "SELECT id FROM work_items WHERE status = 'completed'"
            ).fetchall()
        }
        missing = sorted(dependencies - completed)
        if missing:
            raise ValueError(f"dependencies are not complete: {', '.join(missing)}")
        with self._connection:
            self._connection.execute(
                "UPDATE work_items SET status='completed', result=?, updated_at=? WHERE id=?",
                (result.strip(), datetime.now(UTC).isoformat(), item_id),
            )

    def propose_action(
        self, *, action: str, reason: str, scope: str, evidence: Iterable[str],
        risk: str, validation: str, rollback: str,
    ) -> ActionProposal:
        """Persist an action proposal; never execute it or infer approval."""
        fields = (action, reason, scope, risk, validation, rollback)
        if any(not value.strip() for value in fields):
            raise ValueError("action, reason, scope, risk, validation and rollback are required")
        evidence_tuple = tuple(item.strip() for item in evidence if item.strip())
        if not evidence_tuple:
            raise ValueError("at least one evidence item is required")
        proposal = ActionProposal(
            action=action.strip(), reason=reason.strip(), scope=scope.strip(),
            evidence=evidence_tuple, risk=risk.strip(), validation=validation.strip(),
            rollback=rollback.strip(),
        )
        with self._connection:
            self._connection.execute(
                """INSERT INTO action_proposals
                (action,reason,scope,evidence,risk,validation,rollback,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (proposal.action, proposal.reason, proposal.scope, json.dumps(proposal.evidence),
                 proposal.risk, proposal.validation, proposal.rollback, proposal.status,
                 datetime.now(UTC).isoformat()),
            )
        return proposal

    def close(self) -> None:
        self._connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=".anne/vitavolt_company_engine.sqlite3",
                        help="SQLite database path (default: local .anne directory)")
    parser.add_argument("--next", type=int, default=3, help="number of ready tasks to show")
    args = parser.parse_args()
    engine = VitavoltCompanyEngine(args.db)
    try:
        engine.seed_plan()
        print("ANNE Company Engine — Vitavolt AI Infrastructure Energy MVP")
        print("\nREADY TASKS")
        print(json.dumps(engine.next_work(args.next), ensure_ascii=False, indent=2))
        print("\nALL WORK")
        print(json.dumps(engine.list_work(), ensure_ascii=False, indent=2))
    finally:
        engine.close()


if __name__ == "__main__":
    main()
