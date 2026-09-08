from __future__ import annotations

import base64
import builtins
import io
import importlib.util
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

import pytest

from anne.agent.github_memory import GitHubMemory
from anne.agent.runtime import AnneAgent
from anne.core.agency_gate import ActionDecision, Authorization
from anne.core.anla_score import passes_anla
from anne.core.cognitive_state import Consciousness, EthicScore, Hypothesis
from anne.core.decision_loop import DecisionLoop
from anne.core.failure_recovery import ReframePlan
from anne.core.verification import (
    FactualStatus,
    ReferenceClaim,
    ReferenceVerifier,
    VerificationResult,
    verify_claim,
)
from anne.learning.knowledge_memory import KnowledgeMemory
from anne.memory.fractal_memory import FractalMemory
from anne.memory.local_memory import LocalMemory
from anne.mythos.engine import MitosEngine
from anne.providers.gemini import GeminiProvider
from anne.providers.local import LocalProvider
from anne.safety.policy import ToolPolicy, redact_sensitive

SYNTHETIC_SECRET = "ghp_" + "x" * 32


def test_empty_allowlist_denies_every_tool_and_copies_input():
    allowed = set()
    policy = ToolPolicy(allowed)
    allowed.add("local_read")
    assert not policy.authorize("local_read", {"path": "README.md"}).allowed
    assert ToolPolicy().authorize("local_read", {"path": "README.md"}).allowed


def test_preflight_failure_is_redacted_at_storage_boundary():
    memory = FractalMemory(":memory:")
    try:
        result = DecisionLoop(memory=memory).run("Explain ransomware defenses " + SYNTHETIC_SECRET)
        assert result.status == "ABORTED"
        stored = memory.conn.execute("SELECT raw_input FROM failure_traces").fetchone()[0]
        assert SYNTHETIC_SECRET not in stored
        assert "[REDACTED]" in stored
    finally:
        memory.conn.close()


def test_all_fractal_write_paths_redact_new_text():
    memory = FractalMemory(":memory:")
    try:
        hypothesis = Hypothesis("h1", SYNTHETIC_SECRET, SYNTHETIC_SECRET, 0.8)
        memory.save_hypothesis(hypothesis)
        memory.save_decision(
            "d1", "h1", EthicScore(1, 1, 0, 0.8, "ONAYLA", SYNTHETIC_SECRET),
            [Consciousness(SYNTHETIC_SECRET)],
        )
        memory.save_dream_pattern(SYNTHETIC_SECRET, 0.8, "ONAYLA")
        memory.save_dream_pattern(SYNTHETIC_SECRET, 0.9, "ONAYLA")
        memory.save_learned_rule(SYNTHETIC_SECRET, 0.8)
        memory.save_learned_rule(SYNTHETIC_SECRET, 0.9)
        memory.update_empathy(SYNTHETIC_SECRET, "user")
        memory.save_scale_event(
            cycle_id="c1", parent_cycle_id=None, depth=0, scale_role="frame",
            task_mode="general", question=SYNTHETIC_SECRET, selected_claim=SYNTHETIC_SECRET,
            status="started", stage_reached="DUY",
        )
        dumped = "\n".join(memory.conn.iterdump())
        assert SYNTHETIC_SECRET not in dumped
        assert "[REDACTED]" in dumped
        assert memory.conn.execute("SELECT frequency FROM dream_patterns").fetchone()[0] == 2
        assert memory.conn.execute("SELECT support_count FROM learned_rules").fetchone()[0] == 2
    finally:
        memory.conn.close()


def test_local_memory_redacts_and_reopens(tmp_path):
    path = tmp_path / "local.db"
    memory = LocalMemory(path)
    memory.save(SYNTHETIC_SECRET, SYNTHETIC_SECRET, SYNTHETIC_SECRET)
    memory.conn.close()
    reopened = LocalMemory(path)
    try:
        assert SYNTHETIC_SECRET not in reopened.context()
        assert "[REDACTED]" in reopened.context()
    finally:
        reopened.conn.close()


def test_named_and_batch_sql_parameters_are_redacted():
    memory = LocalMemory(":memory:")
    try:
        memory.conn.execute("CREATE TABLE probe(value TEXT)")
        memory.conn.execute("INSERT INTO probe VALUES (:value)", {"value": SYNTHETIC_SECRET})
        memory.conn.executemany("INSERT INTO probe VALUES (?)", [(SYNTHETIC_SECRET,)])
        memory.conn.cursor().executemany("INSERT INTO probe VALUES (?)", [(SYNTHETIC_SECRET,)])
        assert memory.conn.execute("SELECT value FROM probe").fetchall() == [("[REDACTED]",)] * 3
    finally:
        memory.conn.close()


def test_knowledge_memory_redacts_structured_fields(tmp_path):
    path = tmp_path / "knowledge.json"
    memory = KnowledgeMemory(path)
    memory.save_term(term="test", meaning=SYNTHETIC_SECRET, source=SYNTHETIC_SECRET)
    assert SYNTHETIC_SECRET not in path.read_text()
    assert memory.get_term("test")["status"] == "LEARNED_CANDIDATE"


def test_github_memory_redacts_before_outbound_write(monkeypatch):
    captured = []

    @contextmanager
    def fake_open(request, timeout):
        body = json.loads(request.data)
        captured.append(json.loads(base64.b64decode(body["content"])))
        yield io.BytesIO(b'{"content":{"path":"memory/test.json"}}')

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    memory = GitHubMemory(token="synthetic-transport-token", repository="test/test")
    memory.save(SYNTHETIC_SECRET, SYNTHETIC_SECRET, SYNTHETIC_SECRET)
    assert SYNTHETIC_SECRET not in json.dumps(captured)
    assert captured[0]["user_input"] == "[REDACTED]"


def test_cloud_sdk_is_only_required_when_constructing_gemini(monkeypatch):
    original_import = builtins.__import__

    def block_google(name, *args, **kwargs):
        if name == "google" or name.startswith("google."):
            raise ImportError("SDK deliberately unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_google)
    assert LocalProvider().backend == "openai_compatible"
    with pytest.raises(RuntimeError, match="optional SDK"):
        GeminiProvider(api_key="synthetic")


@pytest.mark.parametrize("claim", [
    "The capital of France is Rome.",
    "Fransa’nın başkenti Berlin’dir.",
])
def test_heuristic_pass_does_not_imply_factual_verification(claim):
    assert passes_anla(claim)[0]
    assert verify_claim(claim).status == FactualStatus.UNVERIFIED


def test_distinct_subjects_do_not_trigger_opposite_word_rejection():
    assert passes_anla("Some statements are true and others are false.")[0]
    assert not passes_anla("The claim is true and false in the exact same interpretation.")[0]


def test_reference_verification_requires_complete_matching_claims():
    verifier = ReferenceVerifier((ReferenceClaim("Result A", "observation:1", True),))
    assert verify_claim("Result A", verifier).status == FactualStatus.VERIFIED
    assert verify_claim("Result A plus an invented claim", verifier).status == FactualStatus.UNVERIFIED
    assert verify_claim("Result a", verifier).status == FactualStatus.UNVERIFIED


def test_conflicting_references_do_not_verify():
    verifier = ReferenceVerifier((
        ReferenceClaim("Result", "observation:1", True),
        ReferenceClaim("Result", "observation:2", False),
    ))
    assert verify_claim("Result", verifier).status == FactualStatus.CONFLICTING


@pytest.mark.parametrize("result", [
    VerificationResult(FactualStatus.VERIFIED),
    VerificationResult(FactualStatus.VERIFIED, ("",)),
    VerificationResult("invalid", ("source",)),
    VerificationResult(FactualStatus.VERIFIED, "not-a-tuple"),
])
def test_malformed_verifier_output_fails_closed(result):
    class BadVerifier:
        def verify(self, claim):
            return result

    assert verify_claim("Result", BadVerifier()).status == FactualStatus.UNVERIFIED


def test_verifier_exception_fails_closed_without_leaking_details():
    class BrokenVerifier:
        def verify(self, claim):
            raise RuntimeError(SYNTHETIC_SECRET)

    result = verify_claim("Result", BrokenVerifier())
    assert result.status == FactualStatus.UNVERIFIED
    assert SYNTHETIC_SECRET not in result.reason


class StubLocal(LocalProvider):
    def ask(self, prompt, system_instruction=None):
        return (
            "<RESPONSE>The capital of France is Rome.</RESPONSE>"
            "<LEARNING>Remember this assertion.</LEARNING><CONFIDENCE>0.99</CONFIDENCE>"
        )


@pytest.mark.parametrize("strict,supported,expected_withheld", [
    (False, None, False), (True, None, True), (False, False, True), (True, True, False),
])
def test_agent_factual_policy_uses_independent_verifier(tmp_path, strict, supported, expected_withheld):
    local_memory = LocalMemory(":memory:")
    core_memory = FractalMemory(":memory:")
    verifier = None if supported is None else ReferenceVerifier((
        ReferenceClaim("The capital of France is Rome.", "synthetic:test-reference", supported),
    ))
    try:
        agent = AnneAgent(
            StubLocal(), local_memory, workspace=tmp_path,
            decision_loop=DecisionLoop(memory=core_memory), response_verifier=verifier,
            require_verified_response=strict,
        )
        result = agent.run("Describe the capital")
        assert result.verification["response_withheld"] is expected_withheld
        if expected_withheld:
            assert "France is Rome" not in result.response
            assert result.confidence <= 0.2
        elif supported is None:
            assert result.verification["status"] == "unverified"
            assert result.learning.startswith("UNVERIFIED MODEL SUGGESTION")
    finally:
        local_memory.conn.close()
        core_memory.conn.close()


def test_agency_denial_prevents_tool_execution(tmp_path, monkeypatch):
    local_memory = LocalMemory(":memory:")
    core_memory = FractalMemory(":memory:")
    try:
        agent = AnneAgent(
            StubLocal(), local_memory, workspace=tmp_path,
            decision_loop=DecisionLoop(memory=core_memory),
        )
        calls = []
        agent.tools["local_read"] = lambda **arguments: calls.append(arguments)
        monkeypatch.setattr(
            agent.agency_gate, "authorize",
            lambda *args, **kwargs: Authorization(ActionDecision.REVIEW, "review required"),
        )
        assert not agent._execute_tool("local_read", {"path": "sample.txt"})["ok"]
        assert not calls
    finally:
        local_memory.conn.close()
        core_memory.conn.close()


def test_mitos_scores_are_explicitly_simulated_and_reproducible():
    first = MitosEngine(seed=4).generate("bounded task", batch_size=2)
    second = MitosEngine(seed=4).generate("bounded task", batch_size=2)
    assert [asdict(candidate) for candidate in first] == [asdict(candidate) for candidate in second]
    assert all(candidate.evidence_status == "SIMULATION" for candidate in first)
    assert all(candidate.score_origin == "seeded_random_fixture" for candidate in first)


def test_redaction_is_idempotent():
    once = redact_sensitive("token=" + SYNTHETIC_SECRET)
    assert redact_sensitive(once) == once


def test_repeated_rules_do_not_inflate_confidence():
    memory = FractalMemory(":memory:")
    try:
        for attempt in range(5):
            memory.save_learned_rule("repeated observation", 0.4)
        confidence, count = memory.conn.execute(
            "SELECT confidence,support_count FROM learned_rules"
        ).fetchone()
        assert confidence == pytest.approx(0.4)
        assert count == 5
    finally:
        memory.conn.close()


def test_cognitive_cycles_do_not_overwrite_previous_hypotheses():
    memory = FractalMemory(":memory:")
    try:
        loop = DecisionLoop(memory=memory)
        for attempt in range(2):
            result = loop.run_cognitive("Explore a bounded technical option", seed=7)
            assert result.state.output["candidate_evidence_status"] == "SIMULATION"
        assert memory.conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0] == 2
    finally:
        memory.conn.close()


def test_retry_rechecks_fail_fast_and_persists_lineage(monkeypatch):
    memory = FractalMemory(":memory:")
    try:
        loop = DecisionLoop(memory=memory)
        monkeypatch.setattr("anne.core.pipeline.passes_anla", lambda *args, **kwargs: (False, 0.1))
        monkeypatch.setattr(
            "anne.core.cognitive_orchestrator.FailureRecoveryController.plan",
            lambda failure, question, attempt: ReframePlan(
                "unsafe-test", "ransomware", failure.cycle_id, 1, attempt,
            ),
        )
        result = loop.run_cognitive("Explore a bounded technical option", seed=7)
        assert result.status == "ABORTED"
        assert result.stop_reason == "fail_fast"
        assert result.retry_count == 1
        parent, depth = memory.conn.execute(
            "SELECT parent_cycle_id,depth FROM failure_traces WHERE stage='FAIL_FAST'"
        ).fetchone()
        assert parent == result.lineage[0]
        assert depth == 1
    finally:
        memory.conn.close()


def test_retry_cannot_drop_original_evidence_requirement(monkeypatch):
    memory = FractalMemory(":memory:")
    try:
        loop = DecisionLoop(memory=memory)
        monkeypatch.setattr(
            "anne.core.cognitive_orchestrator.FailureRecoveryController.plan",
            lambda failure, question, attempt: ReframePlan(
                "drop-evidence-test", "Explore a bounded technical option", failure.cycle_id, 1, attempt,
            ),
        )
        result = loop.run_cognitive("Bu iddianın kanıtı nedir?", seed=7)
        assert result.status != "EXECUTED"
        assert result.state.requires_evidence
        assert result.state.output["action"] == "HALT"
    finally:
        memory.conn.close()


def test_ablation_does_not_claim_parent_workspace_revision(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "benchmarks/scripts/run_anla_ablation.py"
    spec = importlib.util.spec_from_file_location("review_ablation", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.git_sha() == "unknown"