from __future__ import annotations

import json
from pathlib import Path

from anne.learning.experience_learning import Experience
from anne.learning.strategy_adaptation import StrategyAdapter

ROOT = Path(__file__).resolve().parents[1]


def _load_fixture() -> dict[str, object]:
    return json.loads(
        (ROOT / "benchmarks" / "learning_strategy_adaptation_v01.json").read_text(
            encoding="utf-8"
        )
    )


def test_strategy_adaptation_fixture_matches_contract() -> None:
    fixture = _load_fixture()
    adapter = StrategyAdapter()

    for case in fixture["cases"]:
        experiences = tuple(
            Experience(
                source_cycle_id=item["source_cycle_id"],
                outcome=item["outcome"],
                failure_class=item["failure_class"],
                strategy=item["strategy"],
                lesson="synthetic fixture observation",
                safe_to_reuse=False,
                factual_status="UNVERIFIED",
            )
            for item in case["experiences"]
        )
        decision = adapter.adapt(case["current_strategy"], experiences)
        assert decision.action == case["expected_action"], case["id"]
        assert decision.strategy == case["expected_strategy"], case["id"]


def test_repeated_failure_changes_strategy_but_single_failure_does_not() -> None:
    adapter = StrategyAdapter()
    one = Experience(
        source_cycle_id="c1",
        outcome="FAILURE",
        failure_class="evidence_gap",
        strategy="research",
        lesson="synthetic",
        safe_to_reuse=False,
        factual_status="UNVERIFIED",
    )
    two = one.__class__(**{**one.__dict__, "source_cycle_id": "c2"})

    assert adapter.adapt("research", (one,)).action == "KEEP"
    decision = adapter.adapt("research", (one, two))
    assert decision.action == "CHANGE"
    assert decision.strategy == "seek_fresh_independent_evidence"


def test_safety_failures_never_map_to_an_automatic_strategy_change() -> None:
    adapter = StrategyAdapter()
    failures = tuple(
        Experience(
            source_cycle_id=f"c{i}",
            outcome="FAILURE",
            failure_class="execution_risk",
            strategy="execute",
            lesson="synthetic",
            safe_to_reuse=False,
            factual_status="UNVERIFIED",
        )
        for i in (1, 2)
    )

    decision = adapter.adapt("execute", failures)
    assert decision.action == "ABSTAIN"
    assert decision.strategy == "require_authority_review"
