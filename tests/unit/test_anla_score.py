"""Unit tests for heuristic ANLA score."""

from anne.core.anla_score import (
    compute_anla_score,
    context_consistency,
    logical_coherence,
    passes_anla,
    select_top_candidates,
    token_overlap,
    trace_awareness,
)


def test_contradiction_low_score():
    text = "Water boils at 100C and also never boils under any pressure."
    assert logical_coherence(text) == 0.0
    s = compute_anla_score(text)
    assert s < 0.5


def test_coherent_passes():
    text = "Water boils at 100 degrees Celsius at standard atmospheric pressure."
    ok, s = passes_anla(text)
    assert ok is True
    assert s >= 0.5


def test_france_berlin_penalty():
    text = "The capital of France is Berlin according to this draft."
    assert logical_coherence(text) < 1.0


def test_empty_text_fails():
    ok, s = passes_anla("")
    assert ok is False
    assert s == 0.0


def test_always_never_pair():
    text = "This statement is always true and never true under all conditions."
    assert logical_coherence(text) == 0.0


def test_trace_awareness_graduated():
    failures = [("ft1", "c1", "ANLA", "S_ANLA=0.2 water never boils pressure", "", 0.0, "")]
    soft = trace_awareness("unrelated astronomy claim about stars", failures)
    assert soft >= 0.8
    hard = trace_awareness("water never boils under pressure again", failures)
    assert hard <= 0.5


def test_select_top_candidates_orders_by_score():
    cands = [
        "Water boils at 100C and also never boils under any pressure.",
        "Paris is the capital of France and is located in Europe.",
        "",
    ]
    top = select_top_candidates(cands, top_k=2)
    assert len(top) == 2
    assert top[0][1] >= top[1][1]
    assert "Paris" in top[0][0]


def test_token_overlap_empty():
    assert token_overlap("", "abc") == 0.0

def test_context_consistency_relevant_candidate_scores_higher():
    context = "solar roof system with battery storage"
    relevant = "battery storage for a solar roof system"
    unrelated = "olive oil factory water treatment"
    assert context_consistency(context, relevant) > context_consistency(context, unrelated)


def test_context_consistency_is_sensitive_to_input():
    candidate = "solar roof system with battery storage"
    unrelated_input = "olive oil factory water treatment"
    assert context_consistency(candidate, candidate) > context_consistency(
        unrelated_input, candidate
    )


def test_context_consistency_empty_inputs_are_fail_safe():
    assert context_consistency("", "candidate") == 0.0
    assert context_consistency("context", "") == 0.0
    assert context_consistency(" ", "candidate") == 0.0


def test_context_consistency_long_unrelated_candidate_is_not_high():
    context = "solar roof system"
    long_unrelated = " ".join(["olive", "oil", "factory", "water", "treatment"] * 20)
    assert context_consistency(context, long_unrelated) == 0.0


def test_trace_effect_is_separate_from_context_consistency():
    context = "solar roof system"
    candidate = "solar roof system with battery"
    failures = [
        ("ft1", "c1", "ANLA", "unrelated failure reason", "", 0.0, ""),
    ]
    assert context_consistency(context, candidate) == context_consistency(context, candidate)
    without_trace = compute_anla_score(candidate, context=context)
    with_trace = compute_anla_score(candidate, failures, context=context)
    assert with_trace <= without_trace
