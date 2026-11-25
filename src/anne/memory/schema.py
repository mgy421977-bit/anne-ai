"""ARCH-MGY-26 v1.0 envelope and SQLite schema definitions."""

from __future__ import annotations

import json
from typing import Any

PROTOCOL = "ARCH-MGY-26"
PROTOCOL_VERSION = "1.0"
MEMORY_TIERS = ("L1", "L2", "L3")
STATUSES = (
    "CANDIDATE",
    "VERIFIED",
    "SEAL_CANDIDATE",
    "SEALED",
    "SUPERSEDED",
    "REVOKED",
    "STALE",
    "ARCHIVED",
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memory_records (
    record_id TEXT PRIMARY KEY,
    protocol TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    memory_tier TEXT NOT NULL CHECK(memory_tier IN ('L1','L2','L3')),
    domain TEXT NOT NULL,
    record_key TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    filter_json TEXT NOT NULL,
    lifecycle_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    supersedes_record_id TEXT,
    UNIQUE(domain, record_key, record_id)
);
CREATE INDEX IF NOT EXISTS idx_memory_records_lookup
    ON memory_records(domain, record_key, memory_tier, status);
CREATE TABLE IF NOT EXISTS memory_evidence (
    evidence_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL REFERENCES memory_records(record_id),
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    independence_group TEXT NOT NULL,
    observed_at TEXT,
    retrieved_at TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT '',
    evidence_kind TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    provenance TEXT NOT NULL,
    source_authority REAL NOT NULL DEFAULT 0.3
);
CREATE INDEX IF NOT EXISTS idx_memory_evidence_record ON memory_evidence(record_id);
CREATE TABLE IF NOT EXISTS memory_events (
    event_id TEXT PRIMARY KEY,
    record_id TEXT,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT,
    event_payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_conflicts (
    conflict_id TEXT PRIMARY KEY,
    record_a TEXT NOT NULL,
    record_b TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    resolution TEXT,
    detected_at TEXT NOT NULL,
    resolved_at TEXT
);
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_envelope(envelope: dict[str, Any]) -> None:
    required = {
        "protocol",
        "protocol_version",
        "record_id",
        "memory_tier",
        "domain",
        "key",
        "payload",
        "evidence",
        "anne_ai_filter",
        "lifecycle",
    }
    missing = required.difference(envelope)
    if missing:
        raise ValueError(f"missing envelope fields: {sorted(missing)}")
    if envelope["protocol"] != PROTOCOL or envelope["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError("unsupported ARCH-MGY-26 protocol")
    if envelope["memory_tier"] not in MEMORY_TIERS:
        raise ValueError("memory_tier must be L1, L2, or L3")
    if not isinstance(envelope["payload"], dict):
        raise TypeError("payload must be an object")
    if not isinstance(envelope["evidence"], list):
        raise TypeError("evidence must be a list")


__all__ = ["PROTOCOL", "PROTOCOL_VERSION", "SCHEMA_SQL", "canonical_json", "validate_envelope"]
