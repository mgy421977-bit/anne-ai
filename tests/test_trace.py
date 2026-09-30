from anne.core.trace import TRACE_SCHEMA_VERSION, CycleTrace, trace_from_runtime


def test_cycle_trace_serializes_deterministically() -> None:
    trace = CycleTrace(
        cycle_id="or_1",
        status="EXECUTED",
        stage_trace=("FAIL_FAST", "DUY", "YAP"),
        intent={"requires_evidence": False, "intent": "general"},
        decision={"action": "PROCEED", "verdict": "ONAYLA"},
    )
    assert trace.schema_version == TRACE_SCHEMA_VERSION
    assert trace.to_json() == trace.to_json()
    assert '"cycle_id":"or_1"' in trace.to_json()
    assert '"schema_version":"1.2"' in trace.to_json()


def test_cycle_trace_rejects_invalid_retry_count() -> None:
    try:
        CycleTrace(cycle_id="or_1", status="BOUNDED", retry_count=-1)
    except ValueError as exc:
        assert "retry_count" in str(exc)
    else:
        raise AssertionError("negative retry_count must be rejected")


def test_runtime_adapter_does_not_turn_confidence_into_decision_fact() -> None:
    trace = trace_from_runtime(
        cycle_id="or_2",
        status="BOUNDED",
        stage_trace=("FAIL_FAST", "DUY", "ANLA"),
        stop_reason="retry_budget_exhausted",
        retry_count=1,
        lineage=("or_1", "or_2"),
        output={
            "verdict": "ABSTAIN",
            "action": "HALT",
            "reason": "verification required",
            "agency_decision": "DENY",
            "factual_status": "unverified",
            "confidence": 0.99,
        },
        context={
            "intent": "query",
            "intent_confidence": 0.8,
            "ambiguity": 0.1,
            "requires_evidence": True,
            "verification_status": "unverified",
            "evidence_status": "unverified",
            "evidence_verified": False,
            "verification_sources": (),
            "verification_reason": "insufficient independent support",
        },
    )
    payload = trace.as_dict()
    assert payload["parent_cycle_id"] == "or_1"
    assert payload["verification"]["verification_status"] == "unverified"
    assert payload["decision"]["action"] == "HALT"
    assert payload["agency"]["agency_decision"] == "DENY"
    assert "confidence" not in payload["decision"]


def test_runtime_adapter_preserves_inference_observations_without_promoting_them() -> None:
    trace = trace_from_runtime(
        cycle_id="or_3",
        status="BOUNDED",
        stage_trace=("DUY", "BAK", "GÖR"),
        stop_reason="research_required",
        retry_count=0,
        lineage=("or_3",),
        context={
            "joint_inferences": (
                {
                    "claim": "A and B jointly imply X",
                    "status": "derived",
                    "source_independence": {"status": "multiple_publisher_families"},
                },
            ),
            "derived_hypotheses": (
                {
                    "id": "DH1",
                    "claim": "A and B jointly imply X",
                    "status": "PROPOSED",
                },
            ),
        },
    )
    payload = trace.as_dict()
    assert payload["joint_inferences"][0]["status"] == "derived"
    assert payload["derived_hypotheses"][0]["status"] == "PROPOSED"
    assert "decision" not in payload["joint_inferences"][0]
    assert "authority" not in payload["joint_inferences"][0]


def test_cycle_trace_round_trips_inference_observations() -> None:
    trace = CycleTrace(
        cycle_id="or_4",
        status="BOUNDED",
        joint_inferences=(
            {"claim": "A and B imply X", "status": "unverified_premises"},
        ),
        derived_hypotheses=(
            {"id": "DH1", "status": "PROPOSED"},
        ),
    )
    restored = CycleTrace.from_dict(trace.as_dict())
    assert restored == trace


def test_runtime_adapter_preserves_re_evaluation_observations() -> None:
    trace = trace_from_runtime(
        cycle_id="or_5",
        status="BOUNDED",
        stage_trace=("INVALIDATION", "RESEARCH", "VERIFICATION"),
        stop_reason="re_evaluation_complete",
        retry_count=0,
        lineage=("or_5",),
        context={
            "re_evaluation": {
                "action": "RESEARCH",
                "target_node": "A1",
                "verification_status": "verified",
                "replacement": "A1:re1",
            },
        },
    )
    payload = trace.as_dict()
    assert payload["re_evaluation"]["action"] == "RESEARCH"
    assert payload["re_evaluation"]["verification_status"] == "verified"
    assert payload["re_evaluation"]["replacement"] == "A1:re1"
    assert "authority" not in payload["re_evaluation"]


def test_cycle_trace_round_trips_re_evaluation_observation() -> None:
    trace = CycleTrace(
        cycle_id="or_6",
        status="BOUNDED",
        re_evaluation={
            "action": "RESEARCH",
            "target_node": "A1",
            "verification_status": "conflicting",
        },
    )
    restored = CycleTrace.from_dict(trace.as_dict())
    assert restored == trace


def test_runtime_adapter_records_explicit_learning_context() -> None:
    trace = trace_from_runtime(
        cycle_id="or_7",
        status="BOUNDED",
        stage_trace=("DUY", "BAK", "GÖR"),
        stop_reason="research_required",
        retry_count=0,
        lineage=("or_7",),
        context={"intent_confidence": 0.99},
        learning_context={
            "key": "web_research",
            "conditions": {"source_count": 2, "freshness": "current"},
        },
    )
    assert trace.learning == {
        "context": {
            "key": "web_research",
            "conditions": {"source_count": 2, "freshness": "current"},
        }
    }


def test_runtime_adapter_does_not_fabricate_learning_context() -> None:
    trace = trace_from_runtime(
        cycle_id="or_8",
        status="BOUNDED",
        stage_trace=("DUY", "ANLA"),
        stop_reason="bounded",
        retry_count=0,
        lineage=("or_8",),
        output={"confidence": 0.99},
        context={"intent_confidence": 0.99, "verification_status": "verified"},
    )
    assert trace.learning == {}


def test_runtime_adapter_keeps_learning_context_explicit() -> None:
    trace = trace_from_runtime(
        cycle_id="or_9",
        status="BOUNDED",
        stage_trace=("DUY", "BAK", "GÖR"),
        stop_reason="bounded",
        retry_count=0,
        lineage=("or_9",),
        context={"learning_context": {"key": "inferred_should_not_be_used"}},
    )
    assert trace.learning == {}


def test_runtime_adapter_records_explicit_strategy() -> None:
    trace = trace_from_runtime(
        cycle_id="or_strategy",
        status="BOUNDED",
        stage_trace=("DUY", "YAP", "RETRY_GATE"),
        stop_reason="retry_authorized",
        retry_count=1,
        lineage=("or_parent", "or_strategy"),
        strategy="recheck_independent_evidence",
    )
    assert trace.learning["strategy"] == "recheck_independent_evidence"
