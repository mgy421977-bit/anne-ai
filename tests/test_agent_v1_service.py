from __future__ import annotations

import json

from tools.anne_vita_agent.service import AuditedAgentService


class FakeAgent:
    def run(self, task):
        if task.get("action") != "vita.ges_precheck":
            return {"status": "DENIED", "reason": "action_not_allowlisted"}
        return {
            "status": "COMPLETED",
            "task_id": "vita.ges_precheck",
            "vita": {
                "result_type": "preliminary_estimate",
                "inputs": {"location": "Izmir", "roof_area_m2": 200},
                "result": {"capacity_kw": 12.4, "num_panels": 20, "annual_kwh": 17980},
                "limitations": ["Not a final engineering design."],
            },
        }


def test_service_writes_report_and_auditable_events_without_email_body(tmp_path):
    service = AuditedAgentService(FakeAgent(), tmp_path)
    result = service.run(
        {
            "action": "vita.ges_precheck",
            "input": {"location": "Izmir"},
            "body": "This raw body must not be written to the journal.",
        }
    )

    assert result["status"] == "COMPLETED"
    report_path = tmp_path / "latest-report.json"
    journal_path = tmp_path / "task-journal.jsonl"
    assert result["report_path"] == str(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "completed"
    assert report["calculation"]["capacity_kw"] == 12.4
    assert report["warnings"] == ["Not a final engineering design."]
    journal_text = journal_path.read_text(encoding="utf-8")
    assert "This raw body must not be written" not in journal_text
    assert '"event": "task.received"' in journal_text
    assert '"event": "task.finished"' in journal_text


def test_service_records_stopped_tasks(tmp_path):
    service = AuditedAgentService(FakeAgent(), tmp_path)
    result = service.run({"action": "shell.exec", "input": {"command": "whoami"}})
    assert result["status"] == "DENIED"
    report = json.loads((tmp_path / "latest-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "denied"
    assert '"event": "task.stopped"' in (tmp_path / "task-journal.jsonl").read_text(encoding="utf-8")
