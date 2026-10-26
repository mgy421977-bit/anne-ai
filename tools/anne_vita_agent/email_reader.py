"""Read-only mailbox boundary for ANNE Agent v1.

No send/reply/forward/delete methods are defined here. Provider integration is
intentionally deferred until the mailbox provider and least-privilege access are known.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MailAttachment:
    name: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class MailMessage:
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    body_text: str
    attachments: tuple[MailAttachment, ...] = ()


class ReadOnlyMailbox(Protocol):
    """Minimum read-only contract for a configured mailbox."""

    def list_messages(self, *, limit: int = 20) -> list[MailMessage]: ...

    def get_message(self, message_id: str) -> MailMessage | None: ...


class MockReadOnlyMailbox:
    """Deterministic in-memory mailbox for tests; it performs no network access."""

    def __init__(self, messages: tuple[MailMessage, ...] = ()) -> None:
        self._messages = {message.message_id: message for message in messages}

    def list_messages(self, *, limit: int = 20) -> list[MailMessage]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("limit must be an integer between 1 and 100")
        messages = sorted(
            self._messages.values(),
            key=lambda message: message.received_at,
            reverse=True,
        )
        return messages[:limit]

    def get_message(self, message_id: str) -> MailMessage | None:
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("message_id must be a non-empty string")
        return self._messages.get(message_id)
