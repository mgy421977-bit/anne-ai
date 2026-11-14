from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from anne.mythos.cloud_field import CloudQuantumField, ThreadWorkerBackend


@dataclass(frozen=True)
class Candidate:
    id: str
    score: float


def evaluate(items: list[Candidate], seed: str = "repeatable") -> object:
    return CloudQuantumField(ThreadWorkerBackend(max_workers=2)).evaluate(
        items,
        candidate_id=lambda item: item.id,
        score=lambda item: item.score,
        seed=seed,
    )


def test_field_is_reproducible_and_normalized() -> None:
    items = [Candidate("a", 0.8), Candidate("b", 0.4), Candidate("c", 0.2)]
    first = evaluate(items)
    second = evaluate(items)
    assert first == second
    assert math.isclose(sum(state.probability for state in first.states), 1.0)
    assert first.authority == "PROPOSAL_ONLY"


def test_field_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        evaluate([Candidate("same", 0.2), Candidate("same", 0.7)])


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -0.1, 1.1, True, "0.5"])
def test_field_rejects_invalid_scores(bad_score: object) -> None:
    with pytest.raises(ValueError):
        evaluate([Candidate("bad", bad_score)])  # type: ignore[arg-type]


def test_empty_field_is_safe() -> None:
    result = evaluate([])
    assert result.states == ()
    assert result.authority == "PROPOSAL_ONLY"


def test_backend_rejects_invalid_worker_count() -> None:
    with pytest.raises(ValueError):
        ThreadWorkerBackend(max_workers=0)
