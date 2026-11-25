from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from anne.memory.fractal_memory import FractalMemoryEngine, sanitize_l3_input


def evidence(group: str, index: int, confidence: float = 0.9) -> dict[str, object]:
    return {
        "source_id": f"source-{group}-{index}",
        "source_type": "PRIMARY_OFFICIAL" if group == "official" else "PEER_REVIEWED_OR_SPEC",
        "independence_group": group,
        "evidence_kind": "OBSERVATION",
        "confidence": confidence,
        "provenance": f"{group}:section-{index}",
    }


def test_l3_redacts_secret_and_pii(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    record_id = engine.ingest_l3(
        "technical_engineering",
        "redaction",
        {"text": "email a@example.com token=ghp_abcdefghijklmnopqrstuvwxyz phone 05551234567"},
    )
    text = engine._row(record_id)["payload"]["text"]
    assert "a@example.com" not in text
    assert "ghp_abcdefghijklmnopqrstuvwxyz" not in text
    assert "REDACTED" in text


def test_three_evidence_from_two_independent_groups_promotes_to_l2(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    record_id = engine.ingest_l3(
        "regulatory_tax",
        "support",
        {"amount": 10},
        [evidence("official", 1), evidence("official", 2), evidence("peer", 1)],
    )
    assert engine.evaluate_promotion_l2(record_id)
    assert engine._row(record_id)["memory_tier"] == "L2"


def test_three_copies_from_one_group_do_not_promote(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    record_id = engine.ingest_l3(
        "regulatory_tax",
        "support",
        {"amount": 10},
        [evidence("same", 1), evidence("same", 2), evidence("same", 3)],
    )
    assert not engine.evaluate_promotion_l2(record_id)


def test_truth_threshold_blocks_seal_candidate(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    record_id = engine.ingest_l3(
        "technical_engineering",
        "weak",
        {"value": 1},
        [evidence("official", 1, 0.7), evidence("peer", 1, 0.7), evidence("peer", 2, 0.7)],
    )
    assert engine.evaluate_promotion_l2(record_id)
    assert not engine.propose_seal_candidate(record_id)


def test_seal_requires_human_role_and_versions_l1(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    first = engine.ingest_l3(
        "technical_engineering",
        "rule",
        {"value": 1},
        [evidence("official", 1), evidence("peer", 1), evidence("peer", 2)],
    )
    assert engine.evaluate_promotion_l2(first)
    assert engine.propose_seal_candidate(first)
    with pytest.raises(PermissionError):
        engine.approve_seal(first, "agent", "LLM_AGENT")
    rejected = engine.conn.execute(
        "SELECT event_type FROM memory_events WHERE record_id=? ORDER BY created_at DESC LIMIT 1",
        (first,),
    ).fetchone()
    assert rejected[0] == "SEAL_REJECTED"
    engine.approve_seal(first, "mustafa", "ARCHITECT")
    second = engine.ingest_l3(
        "technical_engineering",
        "rule",
        {"value": 2},
        [evidence("official", 3), evidence("peer", 3), evidence("peer", 4)],
    )
    assert engine.evaluate_promotion_l2(second)
    assert engine.propose_seal_candidate(second)
    engine.approve_seal(second, "mustafa", "HUMAN_ADMIN")
    assert engine._row(first)["status"] == "SUPERSEDED"
    assert engine._row(second)["status"] == "SEALED"


def test_archive_boundary_and_restore(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    fresh = engine.ingest_l3("operations_project", "fresh", {"v": 1})
    old = engine.ingest_l3("operations_project", "old", {"v": 1})
    boundary = (datetime.now(UTC) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    older = (datetime.now(UTC) - timedelta(days=30, seconds=1)).isoformat().replace("+00:00", "Z")
    engine.conn.execute(
        "UPDATE memory_records SET created_at=?, updated_at=? WHERE record_id=?",
        (boundary, boundary, fresh),
    )
    engine.conn.execute(
        "UPDATE memory_records SET created_at=?, updated_at=? WHERE record_id=?",
        (older, older, old),
    )
    engine.conn.commit()
    archived = engine.archive_stale_l3(30)
    assert fresh in archived
    assert old in archived
    assert engine.restore_archived(old)
    assert engine._row(old)["status"] == "CANDIDATE"


def test_conflict_is_visible_in_query(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    first = engine.ingest_l3("market_pricing", "price", {"value": 10})
    second = engine.ingest_l3("market_pricing", "price", {"value": 11})
    result = engine.query_fractal("market_pricing", "price")
    assert first != second
    assert result.conflicts
    assert result.conflicts[0]["conflict_type"] == "PAYLOAD_MISMATCH"


def test_same_canonical_payload_is_idempotent(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    first = engine.ingest_l3("technical_engineering", "same", {"b": 2, "a": 1})
    second = engine.ingest_l3("technical_engineering", "same", {"a": 1, "b": 2})
    assert first == second
    assert engine._row(first)["content_hash"] == engine._row(second)["content_hash"]


def test_ingest_rolls_back_on_invalid_evidence(tmp_path):
    engine = FractalMemoryEngine(tmp_path / "memory.db")
    with pytest.raises(ValueError):
        engine.ingest_l3(
            "technical_engineering",
            "rollback",
            {"value": 1},
            [evidence("official", 1), {"source_id": "incomplete"}],
        )
    assert (
        engine.conn.execute(
            "SELECT COUNT(*) FROM memory_records WHERE domain=? AND record_key=?",
            ("technical_engineering", "rollback"),
        ).fetchone()[0]
        == 0
    )


def test_sanitize_helper_is_deterministic():
    value = {"email": "a@example.com", "iban": "TR000000000000000000000000"}
    assert sanitize_l3_input(value) == sanitize_l3_input(value)
