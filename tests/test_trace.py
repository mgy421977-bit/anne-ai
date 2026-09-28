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
    assert '"schema_version":"1.0"' in trace.to_json()


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
