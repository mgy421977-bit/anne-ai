from __future__ import annotations

import sqlite3

import pytest

from anne.core.evidence import EvidenceGate
from anne.core.requirements import EvidenceStatus
from anne.core.verification import FactualStatus
from anne.memory.contextual_memory import ContextualMemoryService
from anne.memory.fractal_memory import FractalMemory


def test_schema_initialization_is_idempotent_and_preserves_existing_memory(tmp_path):
    path = tmp_path / "anne.db"
    legacy = FractalMemory(path)
    legacy.save_failure_trace("legacy-cycle", "ANLA", "old input", "old failure")
    legacy.conn.close()

    first = ContextualMemoryService(path)
    first.create_project("Existing project", project_id="project-a")
    first.conn.close()

    second = ContextualMemoryService(path)
    versions = second.conn.execute(
        "SELECT version FROM memory_schema_version ORDER BY version"
    ).fetchall()
    assert [row[0] for row in versions] == [1]
    assert second.conn.execute("SELECT COUNT(*) FROM failure_traces").fetchone()[0] == 1
    second.conn.close()


def test_project_and_session_isolation_covers_all_context_categories(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project_a = memory.create_project("A", project_id="project-a")
    project_b = memory.create_project("B", project_id="project-b")
    session_a = memory.create_session(project_a, session_id="session-a")
    memory.create_session(project_b, session_id="session-b")

    reason = memory.record_reason(project_a, "decision_reason", {"why": "A"})
    memory.record_event(project_a, "A_EVENT", {"project": "A"}, session_id=session_a)
    memory.checkpoint_state(project_a, "project", {"project": "A"}, session_id=session_a)
    memory.record_decision(project_a, {"text": "A decision"}, reason_record_id=reason)
    memory.record_hypothesis(project_a, existing_hypothesis_id="h-a")
    memory.record_evidence_ref(
        project_a,
        source="tool",
        locator="a://evidence",
        verifier_status=EvidenceStatus.UNVERIFIED,
        provenance="TOOL",
    )
    memory.record_failure(project_a, {"reason": "A failure"})
    memory.add_unresolved_item(project_a, "A item", "A description")
    memory.add_next_action(project_a, "A action", "A description")

    memory.record_event(project_b, "B_EVENT", {"project": "B"})
    memory.checkpoint_state(project_b, "project", {"project": "B"})
    memory.record_failure(project_b, {"reason": "B failure"})
    memory.add_unresolved_item(project_b, "B item", "B description")
    memory.add_next_action(project_b, "B action", "B description")

    context = memory.load_project_context(project_a)
    serialized = repr(context)
    assert "project-b" not in serialized
    assert "B_EVENT" not in serialized
    assert "B failure" not in serialized
    assert context["project"]["project_id"] == project_a
    assert all(row["project_id"] == project_a for row in context["evidence_refs"])
    assert all(row["project_id"] == project_a for row in context["unresolved_items"])
    assert all(row["project_id"] == project_a for row in context["next_actions"])

    session_context = memory.load_project_context(project_a, session_a)
    assert all(row["session_id"] == session_a for row in session_context["recent_events"])


def test_cross_project_relation_is_rejected(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project_a = memory.create_project("A")
    project_b = memory.create_project("B")
    source = memory.record_reason(project_a, "reason", {"project": "A"})
    target = memory.record_reason(project_b, "reason", {"project": "B"})

    with pytest.raises(ValueError, match="different project"):
        memory.add_relation(project_a, source, target, "supports")

    assert memory.conn.execute("SELECT COUNT(*) FROM contextual_relations").fetchone()[0] == 0


def test_state_transition_preserves_previous_state_and_is_deterministic(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    first = memory.checkpoint_state(project, "project", {"version": 1})
    second = memory.checkpoint_state(project, "project", {"version": 2})
    third = memory.checkpoint_state(project, "project", {"version": 3})

    current = memory.get_current_state(project, "project")
    previous = memory.get_previous_state(project, "project")
    assert current["state_id"] == third
    assert current["state_payload"] == {"version": 3}
    assert previous["state_id"] == second
    assert previous["state_payload"] == {"version": 2}
    assert (
        memory.conn.execute(
            "SELECT status FROM contextual_states WHERE state_id=?", (first,)
        ).fetchone()[0]
        == "SUPERSEDED"
    )
    assert (
        memory.conn.execute(
            "SELECT COUNT(*) FROM contextual_events WHERE project_id=?", (project,)
        ).fetchone()[0]
        == 3
    )

    context = memory.load_project_context(project)
    assert context["current_state"]["state_id"] == third
    assert context["previous_state"]["state_id"] == second
    assert len(context["recent_events"]) == 3


def test_decision_supersession_excludes_old_decision_from_active_context(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    old = memory.record_decision(project, {"text": "old"})
    new = memory.record_decision(project, {"text": "new"}, supersedes_decision_id=old)

    context = memory.load_project_context(project)
    assert [row["decision_id"] for row in context["active_decisions"]] == [new]
    assert (
        memory.conn.execute(
            "SELECT decision_status FROM contextual_decisions WHERE decision_id=?", (old,)
        ).fetchone()[0]
        == "SUPERSEDED"
    )
    assert (
        memory.conn.execute(
            "SELECT relation_type FROM contextual_relations WHERE source_record_id=?",
            (old,),
        ).fetchone()[0]
        == "supersedes"
    )


def test_unresolved_and_next_action_lifecycle(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    item = memory.add_unresolved_item(project, "Question", "Needs answer")
    action = memory.add_next_action(project, "Investigate", "Collect context")

    assert memory.load_project_context(project)["unresolved_items"]
    assert memory.load_project_context(project)["next_actions"]
    memory.resolve_unresolved_item(item)
    memory.complete_next_action(action)
    context = memory.load_project_context(project)
    assert context["unresolved_items"] == []
    assert context["next_actions"] == []
    assert (
        memory.conn.execute(
            "SELECT status FROM contextual_unresolved_items WHERE item_id=?", (item,)
        ).fetchone()[0]
        == "RESOLVED"
    )
    assert (
        memory.conn.execute(
            "SELECT status FROM contextual_next_actions WHERE action_id=?", (action,)
        ).fetchone()[0]
        == "COMPLETED"
    )


def test_checkpoint_state_rolls_back_all_records_on_failure(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    memory.checkpoint_state(project, "project", {"version": 1})
    before_states = memory.conn.execute("SELECT COUNT(*) FROM contextual_states").fetchone()[0]
    before_events = memory.conn.execute("SELECT COUNT(*) FROM contextual_events").fetchone()[0]

    with pytest.raises(TypeError):
        memory.checkpoint_state(
            project,
            "project",
            {"version": 2},
            event_payload={"invalid": object()},
        )

    assert (
        memory.conn.execute("SELECT COUNT(*) FROM contextual_states").fetchone()[0] == before_states
    )
    assert (
        memory.conn.execute("SELECT COUNT(*) FROM contextual_events").fetchone()[0] == before_events
    )
    assert memory.get_current_state(project, "project")["state_payload"] == {"version": 1}


def test_evidence_reference_preserves_status_without_verifying_or_mutating_gates(
    tmp_path, monkeypatch
):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("EvidenceGate must not be called by contextual memory")

    monkeypatch.setattr(EvidenceGate, "allows_decision", fail_if_called)
    evidence_id = memory.record_evidence_ref(
        project,
        source="independent-verifier",
        locator="verifier://run/1",
        verifier_status=FactualStatus.VERIFIED,
        provenance="VERIFIER",
    )
    context = memory.load_project_context(project)
    assert context["evidence_refs"][0]["evidence_ref_id"] == evidence_id
    assert context["evidence_refs"][0]["verifier_status"] == "verified"
    assert context["evidence_refs"][0]["provenance"] == "VERIFIER"


def test_verified_memory_reference_does_not_create_available_evidence(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    memory.record_evidence_ref(
        project,
        source="historical-verifier",
        locator="verifier://old",
        verifier_status=FactualStatus.VERIFIED,
        provenance="VERIFIER",
    )
    context = memory.load_project_context(project)
    assert context["evidence_refs"][0]["verifier_status"] == "verified"
    assert EvidenceStatus.AVAILABLE.value not in {
        row["verifier_status"] for row in context["evidence_refs"]
    }


def test_process_restart_persists_context(tmp_path):
    path = tmp_path / "anne.db"
    first = ContextualMemoryService(path)
    project = first.create_project("Restartable", project_id="project-restart")
    first.checkpoint_state(project, "project", {"ready": True})
    first.record_event(project, "checkpoint", {"ok": True})
    first.conn.close()

    second = ContextualMemoryService(path)
    context = second.load_project_context(project)
    assert context["project"]["name"] == "Restartable"
    assert context["current_state"]["state_payload"] == {"ready": True}
    assert context["recent_events"][0]["event_type"] == "checkpoint"
    second.conn.close()


def test_contextual_service_uses_existing_redacting_connection(tmp_path):
    memory = ContextualMemoryService(tmp_path / "anne.db")
    project = memory.create_project("A")
    memory.record_event(project, "secret", {"token": "ghp_" + "x" * 32})
    dumped = "\n".join(memory.conn.iterdump())
    assert "ghp_" + "x" * 32 not in dumped
    assert "[REDACTED]" in dumped
    assert isinstance(memory.conn, sqlite3.Connection)
