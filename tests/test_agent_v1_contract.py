from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from tools.anne_vita_agent.email_reader import (
    MailAttachment,
    MailMessage,
    MockReadOnlyMailbox,
)
from tools.anne_vita_agent.task_journal import TaskJournal, TaskReport


def sample_message(message_id: str, day: int) -> MailMessage:
    return MailMessage(
        message_id=message_id,
        sender="customer@example.com",
        subject="GES ön fizibilite",
        received_at=datetime(2026, 10, day, tzinfo=timezone.utc),
        body_text="Aylık tüketim ve çatı alanı bilgileri ekte.",
        attachments=(MailAttachment("fatura.pdf", "application/pdf", 1024),),
    )


def test_journal_is_append_only_jsonl_and_redacts_secrets(tmp_path):
    journal = TaskJournal(tmp_path / "state" / "journal.jsonl")
    journal.record(
        "task.completed",
        {
            "task_id": "demo-1",
            "api_key": "must-not-be-stored",
            "body": "private email body",
            "result": {"capacity_kw": 12.4},
        },
    )

    entries = journal.read_entries()
    assert len(entries) == 1
    assert entries[0]["details"]["api_key"] == "[REDACTED]"
    assert entries[0]["details"]["body"] == "[OMITTED]"
    assert entries[0]["details"]["result"]["capacity_kw"] == 12.4
    raw = (tmp_path / "state" / "journal.jsonl").read_text(encoding="utf-8")
    assert "must-not-be-stored" not in raw
    assert "private email body" not in raw
    assert json.loads(raw.splitlines()[0])["event"] == "task.completed"


def test_journal_rejects_invalid_event_and_details(tmp_path):
    journal = TaskJournal(tmp_path / "journal.jsonl")
    with pytest.raises(ValueError):
        journal.record(" ", {})
    with pytest.raises(ValueError):
        journal.record("task.started", ["not", "an", "object"])


def test_report_has_a_stable_json_friendly_shape():
    report = TaskReport(
        task_id="ges-001",
        status="needs_input",
        summary="Ön hesaplama için tüketim verisi eksik.",
        inputs={"roof_area_m2": 200},
        missing_data=["daily_consumption_kwh"],
        warnings=["Sonuç üretilemedi; eksik veri tamamlanmalı."],
    )
    payload = report.to_dict()
    assert payload["task_id"] == "ges-001"
    assert payload["status"] == "needs_input"
    assert payload["missing_data"] == ["daily_consumption_kwh"]
    assert json.loads(json.dumps(payload, ensure_ascii=False))["task_id"] == "ges-001"


def test_mock_mailbox_is_read_only_and_sorts_newest_first():
    mailbox = MockReadOnlyMailbox((sample_message("older", 20), sample_message("newer", 21)))
    assert [message.message_id for message in mailbox.list_messages()] == ["newer", "older"]
    assert mailbox.get_message("older").subject == "GES ön fizibilite"
    assert mailbox.get_message("missing") is None
    assert not hasattr(mailbox, "send_email")
    assert not hasattr(mailbox, "reply_email")


@pytest.mark.parametrize("limit", [0, -1, 101, True, "2"])
def test_mock_mailbox_rejects_invalid_limits(limit):
    mailbox = MockReadOnlyMailbox((sample_message("one", 21),))
    with pytest.raises(ValueError):
        mailbox.list_messages(limit=limit)
