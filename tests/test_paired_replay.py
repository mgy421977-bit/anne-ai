import copy

import pytest

from anne.benchmarking import evaluate_replay


def dataset():
    return {
        "split": "development", "model": "synthetic", "generation_settings": {"seed": 0},
        "samples": [
            {"id": "good", "prompt": "Say hello", "response": "Hello there.",
             "expected_acceptable": True, "generation_latency_ms": 2},
            {"id": "bad", "prompt": "Describe the capital", "response": "The capital of France is Rome.",
             "expected_acceptable": False, "generation_latency_ms": 3},
        ],
    }


def test_label_changes_do_not_change_gate_decisions():
    original = dataset()
    altered = copy.deepcopy(original)
    for sample in altered["samples"]:
        sample["expected_acceptable"] = not sample["expected_acceptable"]
    first, second = evaluate_replay(original), evaluate_replay(altered)
    assert [pair["anne"]["accepted"] for pair in first["pairs"]] == [
        pair["anne"]["accepted"] for pair in second["pairs"]
    ]
    assert first["dataset_sha256"] != second["dataset_sha256"]


def test_rates_use_class_denominators_and_report_remaining_false_accepts():
    result = evaluate_replay(dataset())
    assert result["raw"]["false_accept_rate"] == 1.0
    assert result["anne"]["false_accept_rate"] == 1.0
    assert result["anne"]["false_reject_rate"] == 0.0
    assert all(pair["anne"]["factual_status"] == "unverified" for pair in result["pairs"])
    assert result["anne"]["mean_total_latency_ms"] >= result["raw"]["mean_total_latency_ms"]


def test_absent_class_rate_is_undefined_not_zero():
    data = dataset()
    data["samples"] = data["samples"][:1]
    assert evaluate_replay(data)["raw"]["false_accept_rate"] is None


def test_order_does_not_change_gate_outcomes():
    data = dataset()
    first = evaluate_replay(data)
    data["samples"].reverse()
    second = evaluate_replay(data)
    assert {pair["id"]: pair["anne"]["accepted"] for pair in first["pairs"]} == {
        pair["id"]: pair["anne"]["accepted"] for pair in second["pairs"]
    }


@pytest.mark.parametrize("invalid", [None, -1, float("nan"), float("inf"), True])
def test_invalid_latency_is_rejected(invalid):
    data = dataset()
    data["samples"][0]["generation_latency_ms"] = invalid
    with pytest.raises(ValueError, match="latency"):
        evaluate_replay(data)


def test_duplicate_ids_are_rejected():
    data = dataset()
    data["samples"][1]["id"] = "good"
    with pytest.raises(ValueError, match="unique"):
        evaluate_replay(data)