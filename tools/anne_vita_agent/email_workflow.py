"""Conservative email-to-VITA workflow for explicitly selected messages.

Email content is treated as untrusted data. This module extracts a small set of
numeric fields; it never executes instructions found in a message and never sends mail.
"""
from __future__ import annotations

import re
from typing import Any

from .email_reader import ReadOnlyMailbox
from .service import AuditedAgentService
from .task_journal import TaskJournal

_LOCATION = re.compile(r"(?im)^\s*(?:location|konum|il|şehir|sehir)\s*[:=\-]\s*([^\r\n]{2,120})")
_ROOF = re.compile(
    r"(?i)(?:roof\s*area|çatı\s*alanı|cati\s*alani|kullanılabilir\s*çatı)\s*[:=\-]?\s*([\d.,]+)\s*(?:m²|m2|metrekare)?"
)
_CONSUMPTION = re.compile(
    r"(?i)(?:daily\s*consumption|günlük\s*tüketim|gunluk\s*tuketim)\s*[:=\-]?\s*([\d.,]+)\s*(?:kwh\s*/\s*(?:day|gün|gun)|kwh)?"
)


def _number(raw: str) -> float | None:
    value = raw.strip().replace(" ", "")
    # Turkish decimal convention is accepted only when it is unambiguous.
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        tail = value.rsplit(",", 1)[-1]
        value = value.replace(",", ".") if len(tail) <= 2 else value.replace(",", "")
    try:
        return float(value)
    except ValueError:
        return None


def extract_vita_inputs(body_text: str) -> tuple[dict[str, Any], list[str]]:
    """Extract only explicit labelled fields; do not infer missing values."""
    if not isinstance(body_text, str):
        raise ValueError("message body must be text")
    inputs: dict[str, Any] = {}
    missing: list[str] = []

    location_match = _LOCATION.search(body_text)
    roof_match = _ROOF.search(body_text)
    consumption_match = _CONSUMPTION.search(body_text)

    if location_match:
        inputs["location"] = location_match.group(1).strip()
    else:
        missing.append("location")

    if roof_match:
        parsed = _number(roof_match.group(1))
        if parsed is not None:
            inputs["roof_area_m2"] = parsed
        else:
            missing.append("roof_area_m2 (number could not be parsed)")
    else:
        missing.append("roof_area_m2")

    if consumption_match:
        parsed = _number(consumption_match.group(1))
        if parsed is not None:
            inputs["daily_consumption_kwh"] = parsed
        else:
            missing.append("daily_consumption_kwh (number could not be parsed)")
    else:
        missing.append("daily_consumption_kwh")

    return inputs, missing


def process_selected_message(
    *,
    mailbox: ReadOnlyMailbox,
    message_id: str,
    service: AuditedAgentService,
    journal: TaskJournal,
) -> dict[str, Any]:
    """Review one user-selected message and run VITA only if explicit inputs exist."""
    message = mailbox.get_message(message_id)
    if message is None:
        journal.record("email.not_found", {"message_id": message_id})
        return {"status": "NOT_FOUND", "message_id": message_id}

    # Do not journal message body, attachment contents, or credentials.
    journal.record(
        "email.reviewed",
        {
            "message_id": message.message_id,
            "sender": message.sender,
            "subject": message.subject,
            "received_at": message.received_at.isoformat(),
            "attachment_names": [item.name for item in message.attachments],
        },
    )
    inputs, missing = extract_vita_inputs(message.body_text)
    if missing:
        result = {
            "status": "NEEDS_INPUT",
            "message_id": message.message_id,
            "source": {
                "sender": message.sender,
                "subject": message.subject,
                "received_at": message.received_at.isoformat(),
            },
            "extracted_inputs": inputs,
            "missing_data": missing,
            "note": "No VITA calculation was run. Email text is treated as data, not instructions.",
        }
        journal.record(
            "email.needs_input",
            {"message_id": message.message_id, "missing_data": missing},
        )
        return result

    # Explicit allowlisted action only. No text from the email becomes an action name.
    result = service.run({"action": "vita.ges_precheck", "input": inputs})
    result["source"] = {
        "message_id": message.message_id,
        "sender": message.sender,
        "subject": message.subject,
        "received_at": message.received_at.isoformat(),
    }
    result["email_instructions_executed"] = False
    return result
