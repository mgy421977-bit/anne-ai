"""Project-scoped contextual memory on ANNE's existing SQLite foundation.

This module is deliberately independent from the canonical cognitive runtime in
Phase 1.  It stores context and provenance; it never performs verification.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from anne.core.requirements import EvidenceStatus
from anne.core.verification import FactualStatus
from anne.memory.persistence import RedactingConnection, connect_memory

SCHEMA_VERSION = 1

_RECORD_TYPES = {
    "PROJECT",
    "CONTEXT",
    "EVENT",
    "STATE",
    "DECISION",
    "REASON",
    "HYPOTHESIS",
    "EVIDENCE_REF",
    "FAILURE",
    "NEXT_ACTION",
}
_RELATION_TYPES = {
    "caused_by",
    "derived_from",
    "supports",
    "contradicts",
    "supersedes",
    "depends_on",
    "belongs_to",
    "followed_by",
    "changes",
    "addresses",
    "resulted_in",
}
_PROJECT_STATUSES = {"ACTIVE", "ARCHIVED"}
_SESSION_STATUSES = {"ACTIVE", "CLOSED"}
_STATE_STATUSES = {"CURRENT", "SUPERSEDED"}
_DECISION_STATUSES = {"ACTIVE", "SUPERSEDED", "REJECTED", "PENDING"}
_UNRESOLVED_STATUSES = {"OPEN", "RESOLVED", "BLOCKED"}
_ACTION_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", "BLOCKED"}
_PROVENANCE = {"SYSTEM", "USER", "TOOL", "VERIFIER", "MODEL", "IMPORTED"}
_EVIDENCE_STATUSES = {status.value for status in FactualStatus} | {
    EvidenceStatus.UNVERIFIED.value,
    EvidenceStatus.REFUTED.value,
    EvidenceStatus.CONFLICTING.value,
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _row(
    row: sqlite3.Row | tuple[Any, ...] | None, columns: tuple[str, ...]
) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(zip(columns, row, strict=True))


class ContextualMemoryService:
    """Explicit project/session memory API using an existing SQLite connection.

    The service does not automatically capture conversations and does not call
    ClaimVerifier, EvidenceGate, or AgencyGate.  Stored evidence status is an
    imported reference to an independent verifier result, not a new verification.
    """

    def __init__(
        self,
        db_path: str = "anne.db",
        *,
        connection: RedactingConnection | None = None,
    ) -> None:
        self.conn = connection or connect_memory(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS memory_schema_version ("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        current = cur.execute(
            "SELECT COALESCE(MAX(version), 0) FROM memory_schema_version"
        ).fetchone()[0]
        if current < SCHEMA_VERSION:
            self._apply_v1(cur)
            cur.execute(
                "INSERT INTO memory_schema_version(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _now()),
            )
        self.conn.commit()

    @staticmethod
    def _apply_v1(cur: sqlite3.Cursor) -> None:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS contextual_projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE','ARCHIVED'))
            );
            CREATE TABLE IF NOT EXISTS contextual_sessions (
                session_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                created_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL CHECK(status IN ('ACTIVE','CLOSED'))
            );
            CREATE TABLE IF NOT EXISTS contextual_records (
                record_id TEXT PRIMARY KEY,
                record_type TEXT NOT NULL,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                provenance TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contextual_events (
                event_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                event_type TEXT NOT NULL,
                actor_id TEXT,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contextual_states (
                state_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                state_type TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('CURRENT','SUPERSEDED')),
                state_payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                superseded_at TEXT,
                previous_state_id TEXT REFERENCES contextual_states(state_id)
            );
            CREATE TABLE IF NOT EXISTS contextual_decisions (
                decision_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                decision_status TEXT NOT NULL,
                decision_payload TEXT NOT NULL,
                reason_record_id TEXT REFERENCES contextual_records(record_id),
                created_at TEXT NOT NULL,
                superseded_at TEXT
            );
            CREATE TABLE IF NOT EXISTS contextual_evidence_refs (
                evidence_ref_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                claim_id TEXT,
                source TEXT NOT NULL,
                locator TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                verifier_status TEXT NOT NULL,
                provenance TEXT NOT NULL,
                content_hash TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contextual_relations (
                relation_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                source_record_id TEXT NOT NULL,
                target_record_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contextual_unresolved_items (
                item_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                resolution_record_id TEXT
            );
            CREATE TABLE IF NOT EXISTS contextual_next_actions (
                action_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES contextual_projects(project_id),
                session_id TEXT REFERENCES contextual_sessions(session_id),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                related_record_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_contextual_records_scope
                ON contextual_records(project_id, session_id, record_type, created_at);
            CREATE INDEX IF NOT EXISTS idx_contextual_events_scope
                ON contextual_events(project_id, session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_contextual_states_current
                ON contextual_states(project_id, state_type, status, created_at);
            CREATE INDEX IF NOT EXISTS idx_contextual_decisions_active
                ON contextual_decisions(project_id, decision_status, created_at);
            CREATE INDEX IF NOT EXISTS idx_contextual_evidence_scope
                ON contextual_evidence_refs(project_id, session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_contextual_relations_scope
                ON contextual_relations(project_id, relation_type);
            """
        )

    @staticmethod
    def _check(value: str, allowed: set[str], field: str) -> str:
        if value not in allowed:
            raise ValueError(f"invalid {field}: {value}")
        return value

    def _project_exists(self, project_id: str) -> None:
        if (
            self.conn.execute(
                "SELECT 1 FROM contextual_projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            is None
        ):
            raise ValueError(f"unknown project: {project_id}")

    def _session_check(self, project_id: str, session_id: str | None) -> None:
        if session_id is None:
            return
        row = self.conn.execute(
            "SELECT project_id FROM contextual_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown session: {session_id}")
        if row[0] != project_id:
            raise ValueError("session belongs to a different project")

    def _record_exists_in_project(self, record_id: str, project_id: str) -> bool:
        return self._record_project(record_id) == project_id

    def _record_project(self, record_id: str) -> str | None:
        row = self.conn.execute(
            "SELECT project_id FROM contextual_records WHERE record_id = ? "
            "UNION ALL SELECT project_id FROM contextual_events WHERE event_id = ? "
            "UNION ALL SELECT project_id FROM contextual_states WHERE state_id = ? "
            "UNION ALL SELECT project_id FROM contextual_decisions WHERE decision_id = ? "
            "UNION ALL SELECT project_id FROM contextual_evidence_refs WHERE evidence_ref_id = ? "
            "UNION ALL SELECT project_id FROM contextual_unresolved_items WHERE item_id = ? "
            "UNION ALL SELECT project_id FROM contextual_next_actions WHERE action_id = ?",
            (record_id,) * 7,
        ).fetchone()
        return row[0] if row is not None else None

    def create_project(
        self, name: str, *, project_id: str | None = None, status: str = "ACTIVE"
    ) -> str:
        self._check(status, _PROJECT_STATUSES, "project status")
        if not name.strip():
            raise ValueError("project name must not be empty")
        project_id = project_id or _id("project")
        now = _now()
        self.conn.execute(
            "INSERT INTO contextual_projects(project_id,name,created_at,updated_at,status) "
            "VALUES (?,?,?,?,?)",
            (project_id, name.strip(), now, now, status),
        )
        self.conn.commit()
        return project_id

    def create_session(self, project_id: str, *, session_id: str | None = None) -> str:
        self._project_exists(project_id)
        session_id = session_id or _id("session")
        self.conn.execute(
            "INSERT INTO contextual_sessions(session_id,project_id,created_at,ended_at,status) "
            "VALUES (?,?,?,NULL,'ACTIVE')",
            (session_id, project_id, _now()),
        )
        self.conn.commit()
        return session_id

    def close_session(self, session_id: str) -> None:
        row = self.conn.execute(
            "SELECT project_id FROM contextual_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown session: {session_id}")
        now = _now()
        self.conn.execute(
            "UPDATE contextual_sessions SET status='CLOSED', ended_at=? WHERE session_id=?",
            (now, session_id),
        )
        self.conn.execute(
            "UPDATE contextual_projects SET updated_at=? WHERE project_id=?", (now, row[0])
        )
        self.conn.commit()

    def record_record(
        self,
        record_type: str,
        project_id: str,
        *,
        session_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
        status: str = "RECORDED",
        provenance: str | None = None,
        record_id: str | None = None,
    ) -> str:
        self._check(record_type, _RECORD_TYPES, "record type")
        if provenance is not None:
            self._check(provenance, _PROVENANCE, "provenance")
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        record_id = record_id or _id(record_type.lower())
        now = _now()
        self.conn.execute(
            "INSERT INTO contextual_records(record_id,record_type,project_id,session_id,status,"
            "payload,provenance,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                record_type,
                project_id,
                session_id,
                status,
                _json(dict(payload or {})),
                provenance,
                now,
                now,
            ),
        )
        self.conn.execute(
            "UPDATE contextual_projects SET updated_at=? WHERE project_id=?", (now, project_id)
        )
        self.conn.commit()
        return record_id

    def record_event(
        self,
        project_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        actor_id: str | None = None,
        status: str = "RECORDED",
        event_id: str | None = None,
    ) -> str:
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        event_id = event_id or _id("event")
        self.conn.execute(
            "INSERT INTO contextual_events(event_id,project_id,session_id,event_type,actor_id,"
            "payload,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                event_id,
                project_id,
                session_id,
                event_type,
                actor_id,
                _json(dict(payload or {})),
                status,
                _now(),
            ),
        )
        self.conn.commit()
        return event_id

    def save_state(
        self,
        project_id: str,
        state_type: str,
        state_payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        state_id: str | None = None,
        previous_state_id: str | None = None,
    ) -> str:
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        state_id = state_id or _id("state")
        now = _now()
        self.conn.execute(
            "INSERT INTO contextual_states(state_id,project_id,session_id,state_type,status,"
            "state_payload,created_at,superseded_at,previous_state_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                state_id,
                project_id,
                session_id,
                state_type,
                "CURRENT",
                _json(dict(state_payload or {})),
                now,
                None,
                previous_state_id,
            ),
        )
        self.conn.commit()
        return state_id

    def checkpoint_state(
        self,
        project_id: str,
        state_type: str,
        state_payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        event_payload: Mapping[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> str:
        """Atomically supersede the current state, save a new state and append an event."""
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        now = _now()
        previous = self.conn.execute(
            "SELECT state_id FROM contextual_states WHERE project_id=? AND state_type=? "
            "AND status='CURRENT' ORDER BY created_at DESC LIMIT 1",
            (project_id, state_type),
        ).fetchone()
        previous_id = previous[0] if previous else None
        state_id = _id("state")
        event_id = _id("event")
        with self.conn:
            if previous_id:
                self.conn.execute(
                    "UPDATE contextual_states SET status='SUPERSEDED', superseded_at=? "
                    "WHERE state_id=? AND project_id=?",
                    (now, previous_id, project_id),
                )
            self.conn.execute(
                "INSERT INTO contextual_states(state_id,project_id,session_id,state_type,status,"
                "state_payload,created_at,superseded_at,previous_state_id) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    state_id,
                    project_id,
                    session_id,
                    state_type,
                    "CURRENT",
                    _json(dict(state_payload or {})),
                    now,
                    None,
                    previous_id,
                ),
            )
            self.conn.execute(
                "INSERT INTO contextual_events(event_id,project_id,session_id,event_type,actor_id,"
                "payload,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    project_id,
                    session_id,
                    "STATE_TRANSITION",
                    actor_id,
                    _json(dict(event_payload or {"state_id": state_id})),
                    "RECORDED",
                    now,
                ),
            )
            self.conn.execute(
                "UPDATE contextual_projects SET updated_at=? WHERE project_id=?", (now, project_id)
            )
        return state_id

    def record_decision(
        self,
        project_id: str,
        decision_payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        decision_status: str = "ACTIVE",
        reason_record_id: str | None = None,
        supersedes_decision_id: str | None = None,
        decision_id: str | None = None,
    ) -> str:
        self._check(decision_status, _DECISION_STATUSES, "decision status")
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        if reason_record_id and not self._record_exists_in_project(reason_record_id, project_id):
            raise ValueError("reason record is missing or belongs to another project")
        if supersedes_decision_id:
            old = self.conn.execute(
                "SELECT project_id FROM contextual_decisions WHERE decision_id=?",
                (supersedes_decision_id,),
            ).fetchone()
            if old is None or old[0] != project_id:
                raise ValueError("superseded decision is missing or belongs to another project")
        decision_id = decision_id or _id("decision")
        now = _now()
        with self.conn:
            if supersedes_decision_id:
                self.conn.execute(
                    "UPDATE contextual_decisions SET decision_status='SUPERSEDED', superseded_at=? "
                    "WHERE decision_id=? AND project_id=?",
                    (now, supersedes_decision_id, project_id),
                )
            self.conn.execute(
                "INSERT INTO contextual_decisions("
                "decision_id,project_id,session_id,decision_status,"
                "decision_payload,reason_record_id,created_at,superseded_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    decision_id,
                    project_id,
                    session_id,
                    decision_status,
                    _json(dict(decision_payload or {})),
                    reason_record_id,
                    now,
                    None,
                ),
            )
            self.conn.execute(
                "UPDATE contextual_projects SET updated_at=? WHERE project_id=?", (now, project_id)
            )
        if supersedes_decision_id:
            self.add_relation(
                project_id, supersedes_decision_id, decision_id, "supersedes", commit=True
            )
        return decision_id

    def record_hypothesis(
        self,
        project_id: str,
        *,
        existing_hypothesis_id: str | None = None,
        session_id: str | None = None,
        status: str = "HYPOTHESIS",
        payload: Mapping[str, Any] | None = None,
    ) -> str:
        return self.record_record(
            "HYPOTHESIS",
            project_id,
            session_id=session_id,
            payload={"existing_hypothesis_id": existing_hypothesis_id, **dict(payload or {})},
            status=status,
            provenance="SYSTEM",
        )

    def record_reason(
        self,
        project_id: str,
        reason_type: str,
        reason_payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        provenance: str = "SYSTEM",
    ) -> str:
        return self.record_record(
            "REASON",
            project_id,
            session_id=session_id,
            payload=reason_payload,
            status=reason_type,
            provenance=provenance,
        )

    def record_failure(
        self,
        project_id: str,
        payload: Mapping[str, Any] | None = None,
        *,
        session_id: str | None = None,
        provenance: str = "SYSTEM",
    ) -> str:
        return self.record_record(
            "FAILURE",
            project_id,
            session_id=session_id,
            payload=payload,
            status="RECORDED",
            provenance=provenance,
        )

    def record_evidence_ref(
        self,
        project_id: str,
        *,
        source: str,
        locator: str,
        verifier_status: EvidenceStatus | FactualStatus | str = EvidenceStatus.UNVERIFIED,
        provenance: str,
        captured_at: str | None = None,
        claim_id: str | None = None,
        content_hash: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Store an independently produced verification reference; never verify."""
        status = (
            verifier_status.value
            if isinstance(verifier_status, (EvidenceStatus, FactualStatus))
            else verifier_status
        )
        self._check(status, _EVIDENCE_STATUSES, "verifier status")
        self._check(provenance, _PROVENANCE, "provenance")
        if not source.strip() or not locator.strip():
            raise ValueError("source and locator must not be empty")
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        evidence_ref_id = _id("evidence")
        self.conn.execute(
            "INSERT INTO contextual_evidence_refs(evidence_ref_id,project_id,session_id,claim_id,"
            "source,locator,captured_at,verifier_status,provenance,content_hash,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                evidence_ref_id,
                project_id,
                session_id,
                claim_id,
                source,
                locator,
                captured_at or _now(),
                status,
                provenance,
                content_hash,
                _now(),
            ),
        )
        self.conn.commit()
        return evidence_ref_id

    def add_relation(
        self,
        project_id: str,
        source_record_id: str,
        target_record_id: str,
        relation_type: str,
        metadata: Mapping[str, Any] | None = None,
        *,
        commit: bool = True,
    ) -> str:
        self._check(relation_type, _RELATION_TYPES, "relation type")
        self._project_exists(project_id)
        source_project = self._record_project(source_record_id)
        target_project = self._record_project(target_record_id)
        if source_project is not None and source_project != project_id:
            raise ValueError("source record belongs to a different project")
        if target_project is not None and target_project != project_id:
            raise ValueError("target record belongs to a different project")
        if source_project is None:
            raise ValueError("source record is missing or belongs to another project")
        if target_project is None:
            raise ValueError("target record is missing or belongs to another project")
        relation_id = _id("relation")
        self.conn.execute(
            "INSERT INTO contextual_relations(relation_id,project_id,source_record_id,"
            "target_record_id,relation_type,created_at,metadata) VALUES (?,?,?,?,?,?,?)",
            (
                relation_id,
                project_id,
                source_record_id,
                target_record_id,
                relation_type,
                _now(),
                _json(dict(metadata or {})),
            ),
        )
        if commit:
            self.conn.commit()
        return relation_id

    def add_unresolved_item(
        self,
        project_id: str,
        title: str,
        description: str,
        *,
        session_id: str | None = None,
        status: str = "OPEN",
    ) -> str:
        self._check(status, _UNRESOLVED_STATUSES, "unresolved status")
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        item_id = _id("item")
        self.conn.execute(
            "INSERT INTO contextual_unresolved_items("
            "item_id,project_id,session_id,title,description,status,created_at,"
            "resolved_at,resolution_record_id) VALUES (?,?,?,?,?,?,?,NULL,NULL)",
            (item_id, project_id, session_id, title, description, status, _now()),
        )
        self.conn.commit()
        return item_id

    def resolve_unresolved_item(
        self, item_id: str, *, resolution_record_id: str | None = None
    ) -> None:
        row = self.conn.execute(
            "SELECT project_id FROM contextual_unresolved_items WHERE item_id=?", (item_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown unresolved item: {item_id}")
        if resolution_record_id and not self._record_exists_in_project(
            resolution_record_id, row[0]
        ):
            raise ValueError("resolution record is missing or belongs to another project")
        self.conn.execute(
            "UPDATE contextual_unresolved_items SET status='RESOLVED',resolved_at=?,"
            "resolution_record_id=? WHERE item_id=?",
            (_now(), resolution_record_id, item_id),
        )
        self.conn.commit()

    def add_next_action(
        self,
        project_id: str,
        title: str,
        description: str,
        *,
        session_id: str | None = None,
        status: str = "PENDING",
        related_record_id: str | None = None,
    ) -> str:
        self._check(status, _ACTION_STATUSES, "action status")
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        if related_record_id and not self._record_exists_in_project(related_record_id, project_id):
            raise ValueError("related record is missing or belongs to another project")
        action_id = _id("action")
        self.conn.execute(
            "INSERT INTO contextual_next_actions(action_id,project_id,session_id,title,description,"
            "status,created_at,completed_at,related_record_id) VALUES (?,?,?,?,?,?,?,NULL,?)",
            (
                action_id,
                project_id,
                session_id,
                title,
                description,
                status,
                _now(),
                related_record_id,
            ),
        )
        self.conn.commit()
        return action_id

    def complete_next_action(self, action_id: str) -> None:
        if (
            self.conn.execute(
                "SELECT 1 FROM contextual_next_actions WHERE action_id=?", (action_id,)
            ).fetchone()
            is None
        ):
            raise ValueError(f"unknown next action: {action_id}")
        self.conn.execute(
            "UPDATE contextual_next_actions SET status='COMPLETED',completed_at=? "
            "WHERE action_id=?",
            (_now(), action_id),
        )
        self.conn.commit()

    def get_current_state(
        self, project_id: str, state_type: str | None = None
    ) -> dict[str, Any] | None:
        self._project_exists(project_id)
        clauses = ["project_id=?", "status='CURRENT'"]
        params: list[Any] = [project_id]
        if state_type is not None:
            clauses.append("state_type=?")
            params.append(state_type)
        row = self.conn.execute(
            "SELECT state_id,project_id,session_id,state_type,status,state_payload,created_at,"
            "superseded_at,previous_state_id FROM contextual_states WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, rowid DESC LIMIT 1",
            params,
        ).fetchone()
        return self._decode_state(row)

    def get_previous_state(
        self, project_id: str, state_type: str | None = None
    ) -> dict[str, Any] | None:
        self._project_exists(project_id)
        clauses = ["project_id=?", "status='SUPERSEDED'"]
        params: list[Any] = [project_id]
        if state_type is not None:
            clauses.append("state_type=?")
            params.append(state_type)
        row = self.conn.execute(
            "SELECT state_id,project_id,session_id,state_type,status,state_payload,created_at,"
            "superseded_at,previous_state_id FROM contextual_states WHERE "
            + " AND ".join(clauses)
            + " ORDER BY superseded_at DESC, rowid DESC LIMIT 1",
            params,
        ).fetchone()
        return self._decode_state(row)

    def load_project_context(
        self, project_id: str, session_id: str | None = None
    ) -> dict[str, Any]:
        self._project_exists(project_id)
        self._session_check(project_id, session_id)
        scope = " AND session_id = ?" if session_id is not None else ""
        scope_params: tuple[Any, ...] = (project_id,) + ((session_id,) if session_id else ())
        project = _row(
            self.conn.execute(
                "SELECT project_id,name,created_at,updated_at,status FROM contextual_projects "
                "WHERE project_id=?",
                (project_id,),
            ).fetchone(),
            ("project_id", "name", "created_at", "updated_at", "status"),
        )
        current = _row(
            self.conn.execute(
                "SELECT state_id,project_id,session_id,state_type,status,state_payload,created_at,"
                "superseded_at,previous_state_id FROM contextual_states WHERE project_id=? "
                "AND status='CURRENT'"
                + (" AND session_id=?" if session_id else "")
                + " ORDER BY created_at DESC, rowid DESC LIMIT 1",
                scope_params,
            ).fetchone(),
            (
                "state_id",
                "project_id",
                "session_id",
                "state_type",
                "status",
                "state_payload",
                "created_at",
                "superseded_at",
                "previous_state_id",
            ),
        )
        previous = _row(
            self.conn.execute(
                "SELECT state_id,project_id,session_id,state_type,status,state_payload,created_at,"
                "superseded_at,previous_state_id FROM contextual_states WHERE project_id=? "
                "AND status='SUPERSEDED'"
                + (" AND session_id=?" if session_id else "")
                + " ORDER BY superseded_at DESC, rowid DESC LIMIT 1",
                scope_params,
            ).fetchone(),
            (
                "state_id",
                "project_id",
                "session_id",
                "state_type",
                "status",
                "state_payload",
                "created_at",
                "superseded_at",
                "previous_state_id",
            ),
        )
        events = self.conn.execute(
            "SELECT event_id,project_id,session_id,event_type,actor_id,payload,status,created_at "
            "FROM contextual_events WHERE project_id=?"
            + scope
            + " ORDER BY created_at DESC, rowid DESC",
            scope_params,
        ).fetchall()
        decisions = self.conn.execute(
            "SELECT decision_id,project_id,session_id,decision_status,decision_payload,"
            "reason_record_id,created_at,superseded_at FROM contextual_decisions "
            "WHERE project_id=?" + scope + " AND decision_status NOT IN ('SUPERSEDED','REJECTED') "
            "ORDER BY CASE WHEN decision_status='ACTIVE' THEN 0 ELSE 1 END, "
            "created_at DESC, rowid DESC",
            scope_params,
        ).fetchall()
        records = self.conn.execute(
            "SELECT record_id,record_type,project_id,session_id,status,payload,provenance,"
            "created_at,updated_at FROM contextual_records WHERE project_id=?"
            + scope
            + " AND record_type IN ('HYPOTHESIS','FAILURE') ORDER BY created_at DESC, rowid DESC",
            scope_params,
        ).fetchall()
        evidence = self.conn.execute(
            "SELECT evidence_ref_id,project_id,session_id,claim_id,source,locator,captured_at,"
            "verifier_status,provenance,content_hash,created_at FROM contextual_evidence_refs "
            "WHERE project_id=?" + scope + " ORDER BY created_at DESC, rowid DESC",
            scope_params,
        ).fetchall()
        unresolved = self.conn.execute(
            "SELECT item_id,project_id,session_id,title,description,status,created_at,resolved_at,"
            "resolution_record_id FROM contextual_unresolved_items WHERE project_id=?"
            + scope
            + " AND status IN ('OPEN','BLOCKED') "
            "ORDER BY CASE WHEN status='OPEN' THEN 0 ELSE 1 END, created_at ASC, rowid ASC",
            scope_params,
        ).fetchall()
        actions = self.conn.execute(
            "SELECT action_id,project_id,session_id,title,description,status,created_at,"
            "completed_at,"
            "related_record_id FROM contextual_next_actions WHERE project_id=?"
            + scope
            + " AND status IN ('PENDING','IN_PROGRESS','BLOCKED') "
            "ORDER BY CASE WHEN status IN ('PENDING','IN_PROGRESS') THEN 0 ELSE 1 END, "
            "created_at ASC, rowid ASC",
            scope_params,
        ).fetchall()
        return {
            "project": project,
            "current_state": self._decode_state(current),
            "previous_state": self._decode_state(previous),
            "recent_events": [self._decode_payload(row, "payload") for row in events],
            "active_decisions": [
                self._decode_payload(row, "decision_payload") for row in decisions
            ],
            "hypotheses": [
                self._decode_payload(row, "payload") for row in records if row[1] == "HYPOTHESIS"
            ],
            "evidence_refs": [dict(row) for row in evidence],
            "unresolved_items": [dict(row) for row in unresolved],
            "next_actions": [dict(row) for row in actions],
            "failures": [
                self._decode_payload(row, "payload") for row in records if row[1] == "FAILURE"
            ],
        }

    @staticmethod
    def _decode_payload(row: sqlite3.Row, field: str) -> dict[str, Any]:
        result = dict(row)
        with suppress(TypeError, json.JSONDecodeError):
            result[field] = json.loads(result[field])
        return result

    @classmethod
    def _decode_state(cls, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return cls._decode_payload(row, "state_payload")


__all__ = ["ContextualMemoryService", "SCHEMA_VERSION"]
