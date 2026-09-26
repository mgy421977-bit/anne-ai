"""DecisionLoop — mandatory facade over ANNE's guarded cognitive paths."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from anne.core.cognitive_orchestrator import CognitiveOrchestrator, OrchestrationResult
from anne.core.cognitive_state import CognitiveState, Consciousness, Hypothesis
from anne.core.fractal_loop import FractalBudget, FractalResult, FractalThinkingLoop
from anne.core.pipeline import AnnePipeline
from anne.core.resource_profile import ResourceProfile
from anne.core.verification import ClaimVerifier
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.candidate import TaskMode


@dataclass
class DecisionResult:
    status: str
    verdict: str
    action: str
    output: dict[str, Any] = field(default_factory=dict)
    fail_fast: dict[str, Any] | None = None
    anla_score: float | None = None
    ethic_total: float | None = None
    state: CognitiveState | None = None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "verdict": self.verdict,
            "action": self.action,
            "output": self.output,
            "fail_fast": self.fail_fast,
            "anla_score": self.anla_score,
            "ethic_total": self.ethic_total,
            "reason": self.reason,
            "factual_status": self.output.get("factual_status", "unverified"),
        }


class DecisionLoop:
    """Single entry point for the guarded cognitive runtime.

    Both ordinary and cognitive callers enter ``CognitiveOrchestrator``. The
    pipeline remains the stage implementation, but callers cannot skip the
    canonical fail-fast, selection, evidence, agency, and bounded-retry path.
    """

    def __init__(
        self,
        memory: FractalMemory | None = None,
        pipeline: AnnePipeline | None = None,
        anla_enabled: bool = True,
        fail_fast_enabled: bool = True,
        resource_profile: ResourceProfile | None = None,
        memory_db_path: str = "anne.db",
        claim_verifier: ClaimVerifier | None = None,
    ) -> None:
        self.memory = memory or FractalMemory(memory_db_path)
        self.pipeline = pipeline or AnnePipeline(
            memory=self.memory,
            anla_enabled=anla_enabled,
            fail_fast_enabled=fail_fast_enabled,
            claim_verifier=claim_verifier,
        )
        self.resource_profile = resource_profile or ResourceProfile.minimal()
        self.orchestrator = CognitiveOrchestrator(
            self.pipeline,
            resource_profile=self.resource_profile,
        )

    def run(
        self,
        raw_input: str,
        claim: str | None = None,
        parties: Sequence[Consciousness] | None = None,
        hypothesis: Hypothesis | None = None,
        probability: float = 0.7,
        verifier: ClaimVerifier | None = None,
        group_a: Sequence[Consciousness] | None = None,
        group_b: Sequence[Consciousness] | None = None,
    ) -> DecisionResult:
        """Run one request through the canonical orchestrator path."""
        people = list(parties) if parties else [Consciousness(id="user")]
        text_claim = claim if claim is not None else raw_input
        hyp = hypothesis or Hypothesis(
            id=f"h_{uuid4().hex[:12]}",
            topic=text_claim[:48],
            claim=text_claim,
            probability=probability,
            source="decision_loop",
        )
        result = self.orchestrator.run(
            raw_input,
            parties=people,
            hypothesis=hyp,
            verifier=verifier,
            group_a=group_a,
            group_b=group_b,
        )
        if not result.fail_fast.passed:
            return DecisionResult(
                "ABORTED",
                "FAIL_FAST",
                "HALT",
                {
                    "verdict": "FAIL_FAST",
                    "action": "HALT",
                    "reason": result.fail_fast.reason,
                    "rule_id": result.fail_fast.rule_id,
                },
                fail_fast=result.fail_fast.as_dict(),
                reason=result.fail_fast.reason,
            )

        state = result.state
        out = state.output if state is not None else {}
        verdict = out.get("verdict") or (state.action if state else None) or "UNKNOWN"
        action = out.get("action") or ("HALT" if verdict == "REDDET" else "UNKNOWN")
        aborted = (
            result.status != "EXECUTED"
            or verdict in {"REDDET", "FAIL_FAST", "ABSTAIN", "REVIEW"}
            or action in {"HALT", "REVIEW"}
        )
        if verdict == "AYRI_ÇÖZÜM":
            aborted = False
        ethic_total = state.ethic_score.total if state and state.ethic_score else None
        anla_score = state.context_map.get("anla_score") if state else None
        return DecisionResult(
            "ABORTED" if aborted else "EXECUTED",
            str(verdict),
            str(action),
            out,
            result.fail_fast.as_dict(),
            anla_score if isinstance(anla_score, (int, float)) else None,
            ethic_total,
            state,
            str(out.get("reason") or out.get("note") or ""),
        )

    def run_cognitive(
        self,
        raw_input: str,
        *,
        parties: Sequence[Consciousness] | None = None,
        task_mode: TaskMode = TaskMode.GENERAL,
        seed: int | None = None,
        verifier: ClaimVerifier | None = None,
    ) -> OrchestrationResult:
        """Run the executive path with MITOS proposal/ANNE selection."""
        return self.orchestrator.run(
            raw_input,
            parties=parties,
            task_mode=task_mode,
            seed=seed,
            verifier=verifier,
        )

    def run_fractal(
        self,
        raw_input: str,
        claim: str | None = None,
        parties: Sequence[Consciousness] | None = None,
        hypothesis: Hypothesis | None = None,
        probability: float = 0.7,
        *,
        budget: FractalBudget | None = None,
        task_mode: TaskMode = TaskMode.GENERAL,
        verifier: ClaimVerifier | None = None,
    ) -> FractalResult:
        """Run bounded frame → branch → reframe recursion through ANNE gates."""
        people = list(parties) if parties else [Consciousness(id="user")]
        text_claim = claim if claim is not None else raw_input
        hyp = hypothesis or Hypothesis(
            id=f"h_{uuid4().hex[:12]}",
            topic=text_claim[:48],
            claim=text_claim,
            probability=probability,
            source="decision_loop",
        )
        return FractalThinkingLoop(
            self.memory,
            self.pipeline,
            budget=budget,
            resource_profile=self.resource_profile,
            claim_verifier=verifier,
        ).run(
            raw_input,
            hyp,
            parties=people,
            task_mode=task_mode,
        )
