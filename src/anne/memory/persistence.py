"""Credential redaction at parameterized SQLite memory boundaries.

All memory writes must bind data as parameters, never interpolate it into SQL.
This protects new writes; it does not scrub historical databases or arbitrary
binary artifacts. Query parameters are normalized identically to stored values.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Self

from anne.safety.policy import redact_data

Parameters = Sequence[Any] | Mapping[str, Any]


class RedactingCursor(sqlite3.Cursor):
    def execute(self, sql: str, parameters: Parameters = ()) -> Self:
        super().execute(sql, redact_data(parameters))
        return self

    def executemany(self, sql: str, seq_of_parameters: Iterable[Parameters]) -> Self:
        super().executemany(sql, (redact_data(params) for params in seq_of_parameters))
        return self


class RedactingConnection(sqlite3.Connection):
    def cursor(self, factory: Any = None) -> RedactingCursor:
        if factory not in (None, RedactingCursor):
            raise ValueError("Memory cursors must preserve the redaction boundary")
        return super().cursor(factory=RedactingCursor)

    def execute(self, sql: str, parameters: Parameters = ()) -> RedactingCursor:
        return self.cursor().execute(sql, parameters)

    def executemany(
        self, sql: str, seq_of_parameters: Iterable[Parameters]
    ) -> RedactingCursor:
        return self.cursor().executemany(sql, seq_of_parameters)


def connect_memory(db_path: str | Path) -> RedactingConnection:
    return sqlite3.connect(str(db_path), factory=RedactingConnection)