"""Audited service wrapper for the first local ANNE agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .task_journal import TaskJournal, TaskReport


class AuditedAgentService:
    """Wrap a bounded agent, record outcomes, and save a local report.

    The wrapped agent's allowlist remains the execution boundary. Journal entries
    intentionally omit raw task bodies and credentials.
    """

    def __init__(self, agent: Any, workspace: str | Path) -> None:
        self.agent = agent
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.journal = TaskJournal(self.workspace / "task-journal.jsonl")

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(task, dict):
            raise ValueError("task must be a JSON object")
        action = task.get("action")
        self.journal.record("task.received", {"action": action})
        try:
            result = self.agent.run(task)
        except Exception as exc:
            self.journal.record(
                "task.failed",
                {"action": action, "error_type": type(exc).__name__},
            )
            raise

        status = str(result.get("status", "UNKNOWN"))
        self.journal.record(
            "task.finished" if status == "COMPLETED" else "task.stopped",
            {
                "action": action,
                "status": status,
                "task_id": result.get("task_id"),
                "reason": result.get("reason"),
                "vita_result_type": (
                    result.get("vita", {}).get("result_type")
                    if isinstance(result.get("vita"), dict)
                    else None
                ),
            },
        )
        report = self._make_report(action, result)
        report_path = self.workspace / "latest-report.json"
        report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        output = dict(result)
        output["report_path"] = str(report_path)
        output["journal_path"] = str(self.journal.path)
        return output

    @staticmethod
    def _make_report(action: Any, result: dict[str, Any]) -> TaskReport:
        status = str(result.get("status", "UNKNOWN")).lower()
        vita = result.get("vita") if isinstance(result.get("vita"), dict) else {}
        calculation = vita.get("result") if isinstance(vita.get("result"), dict) else {}
        inputs = vita.get("inputs") if isinstance(vita.get("inputs"), dict) else {}
        limitations = vita.get("limitations")
        warnings = list(limitations) if isinstance(limitations, list) else []
        reason = result.get("reason")
        missing_data: list[str] = []
        if reason:
            warnings.append(str(reason))
        if status != "completed":
            summary = f"Task stopped with status: {result.get('status', 'UNKNOWN')}."
        else:
            summary = "VITA preliminary calculation completed; this is not a final engineering design."
        return TaskReport(
            task_id=str(result.get("task_id") or action or "unknown"),
            status=status,
            summary=summary,
            inputs=inputs,
            calculation=calculation,
            assumptions=[
                "VITA output is treated as a preliminary estimate.",
                "Inputs must be confirmed against source documents before engineering use.",
            ],
            warnings=warnings,
            missing_data=missing_data,
            next_steps=(
                ["Review the warnings and validate inputs before using the estimate."]
                if status == "completed"
                else ["Review the reason for stopping and provide corrected inputs or authorization."]
            ),
        )
