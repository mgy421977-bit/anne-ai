from __future__ import annotations

import pytest

from anne.applications.vitavolt_company_engine import (
    VitavoltCompanyEngine,
    VITAVOLT_AI_INFRASTRUCTURE_PLAN,
)


def make_engine(tmp_path):
    engine = VitavoltCompanyEngine(tmp_path / "anne.sqlite3")
    engine.seed_plan()
    return engine


def test_plan_seeds_and_first_tasks_are_ready(tmp_path):
    engine = make_engine(tmp_path)
    try:
        ready = engine.next_work()
        assert [item["id"] for item in ready] == ["market_map"]
        assert len(engine.list_work()) == len(VITAVOLT_AI_INFRASTRUCTURE_PLAN)
    finally:
        engine.close()


def test_dependencies_block_and_then_unlock_work(tmp_path):
    engine = make_engine(tmp_path)
    try:
        with pytest.raises(ValueError, match="dependencies"):
            engine.complete_work("offer", "Drafted offer")
        engine.complete_work("market_map", "Three target segments defined")
        assert [item["id"] for item in engine.next_work()] == ["offer"]
    finally:
        engine.close()


def test_progress_persists_without_overwriting_completed_state(tmp_path):
    db = tmp_path / "anne.sqlite3"
    engine = VitavoltCompanyEngine(db)
    engine.seed_plan()
    engine.complete_work("market_map", "Segments reviewed")
    engine.close()

    engine = VitavoltCompanyEngine(db)
    try:
        engine.seed_plan()
        item = next(item for item in engine.list_work() if item["id"] == "market_map")
        assert item["status"] == "completed"
        assert item["result"] == "Segments reviewed"
    finally:
        engine.close()


def test_action_proposal_requires_evidence_and_never_auto_approves(tmp_path):
    engine = make_engine(tmp_path)
    try:
        with pytest.raises(ValueError, match="evidence"):
            engine.propose_action(
                action="Send outreach", reason="Lead generation", scope="One prospect",
                evidence=[], risk="medium", validation="Draft reviewed", rollback="Do not send",
            )
        proposal = engine.propose_action(
            action="Send outreach", reason="Lead generation", scope="One prospect",
            evidence=["Prospect's official company page"], risk="medium",
            validation="Draft reviewed by founder", rollback="No send; retain draft only",
        )
        assert proposal.status == "PENDING_APPROVAL"
    finally:
        engine.close()


def test_empty_result_and_unknown_task_are_rejected(tmp_path):
    engine = make_engine(tmp_path)
    try:
        with pytest.raises(ValueError, match="empty"):
            engine.complete_work("market_map", " ")
        with pytest.raises(KeyError, match="unknown work item"):
            engine.complete_work("missing", "Done")
    finally:
        engine.close()
