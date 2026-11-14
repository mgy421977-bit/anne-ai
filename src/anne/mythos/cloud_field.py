"""Cloud-hosted, quantum-inspired state-field computation for MITOS.

This module is a classical, deterministic simulation. It does not execute on
quantum hardware and does not grant selection, verification, or action authority.
"""
from __future__ import annotations

import cmath
import hashlib
import math
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class WorkerBackend(Protocol):
    """Execution boundary for local or remote cloud worker implementations."""

    def map(self, function: Callable[[T], R], items: Iterable[T]) -> list[R]: ...


class ThreadWorkerBackend:
    """Bounded local reference backend; cloud adapters can implement WorkerBackend."""

    def __init__(self, max_workers: int = 4) -> None:
        if isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")
        self.max_workers = max_workers

    def map(self, function: Callable[[T], R], items: Iterable[T]) -> list[R]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(function, items))


@dataclass(frozen=True)
class FieldState:
    candidate_id: str
    raw_score: float
    phase_radians: float
    amplitude_real: float
    amplitude_imag: float
    probability: float


@dataclass(frozen=True)
class FieldResult:
    seed: str
    states: tuple[FieldState, ...]
    backend: str
    model: str = "classical_complex_amplitude_interference_v1"
    authority: str = "PROPOSAL_ONLY"


@dataclass(frozen=True)
class _PreparedState:
    candidate_id: str
    score: float
    phase: float


def _phase(seed: str, candidate_id: str) -> float:
    digest = hashlib.sha256(f"{seed}:{candidate_id}".encode("utf-8")).digest()
    integer = int.from_bytes(digest[:8], "big")
    return (integer / (2**64)) * math.tau


class CloudQuantumField:
    """Evaluate bounded candidate amplitudes in a reproducible virtual field.

    The supplied score function is an evaluator, not an authorization gate.
    ANNE's independent CandidateSelector and evidence/agency gates remain
    mandatory after this computation.
    """

    def __init__(self, backend: WorkerBackend | None = None) -> None:
        self.backend = backend or ThreadWorkerBackend()

    def evaluate(
        self,
        candidates: Sequence[T],
        *,
        candidate_id: Callable[[T], str],
        score: Callable[[T], float],
        seed: str,
    ) -> FieldResult:
        if not seed.strip():
            raise ValueError("seed is required")
        if not candidates:
            return FieldResult(seed=seed, states=(), backend=type(self.backend).__name__)
        ids = [candidate_id(item) for item in candidates]
        if any(not isinstance(value, str) or not value.strip() for value in ids):
            raise ValueError("candidate IDs must be non-empty strings")
        if len(set(ids)) != len(ids):
            raise ValueError("candidate IDs must be unique within a field")

        def prepare(item: T) -> _PreparedState:
            value = score(item)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("candidate scores must be numeric")
            numeric = float(value)
            if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
                raise ValueError("candidate scores must be finite and in [0, 1]")
            item_id = candidate_id(item)
            return _PreparedState(item_id, numeric, _phase(seed, item_id))

        prepared = self.backend.map(prepare, candidates)
        amplitudes = [
            cmath.rect(math.sqrt(item.score), item.phase) for item in prepared
        ]
        # A shared reference wave creates constructive/destructive interference.
        # This is a mathematical scoring transform, not physical quantum evolution.
        reference = sum(amplitudes, 0j)
        weighted = [
            amplitude + (reference / len(amplitudes)) * math.sqrt(0.25)
            for amplitude in amplitudes
        ]
        norm = sum(abs(value) ** 2 for value in weighted)
        if not math.isfinite(norm):
            raise ArithmeticError("field normalization became non-finite")
        if norm <= 1e-15:
            probabilities = [0.0 for _ in weighted]
        else:
            probabilities = [abs(value) ** 2 / norm for value in weighted]

        states = tuple(
            FieldState(
                candidate_id=item.candidate_id,
                raw_score=item.score,
                phase_radians=item.phase,
                amplitude_real=weighted[index].real,
                amplitude_imag=weighted[index].imag,
                probability=probabilities[index],
            )
            for index, item in enumerate(prepared)
        )
        return FieldResult(seed=seed, states=states, backend=type(self.backend).__name__)


__all__ = [
    "CloudQuantumField",
    "FieldResult",
    "FieldState",
    "ThreadWorkerBackend",
    "WorkerBackend",
]
