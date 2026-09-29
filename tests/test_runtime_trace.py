from anne.core.decision_loop import DecisionResult


def test_decision_result_as_dict_keeps_factual_status() -> None:
    result = DecisionResult(
        status="ABORTED",
        verdict="REVIEW",
        action="REVIEW",
        output={"factual_status": "unverified"},
    )

    payload = result.as_dict()

    assert payload["status"] == "ABORTED"
    assert payload["factual_status"] == "unverified"
