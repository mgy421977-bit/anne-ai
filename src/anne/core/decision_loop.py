"""DecisionLoop — mandatory facade over ANNE's guarded cognitive paths."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from anne.core.character_integrity import CharacterIntegrityGate
from anne.core.cognitive_orchestrator import CognitiveOrchestrator, OrchestrationResult
from anne.core.cognitive_state import CognitiveState, Consciousness, Hypothesis
from anne.core.fractal_loop import FractalBudget, FractalResult, FractalThinkingLoop
from anne.core.pipeline import AnnePipeline
from anne.core.resource_profile import ResourceProfile
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
    character_integrity: dict[str, Any] | None = None

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
            "factual_status": "unverified",
            "character_integrity": self.character_integrity,
        }


class DecisionLoop:
    """Single entry point; ordinary and fractal paths retain all safety gates."""

    def __init__(
        self,
        memory: FractalMemory | None = None,
        pipeline: AnnePipeline | None = None,
        anla_enabled: bool = True,
        fail_fast_enabled: bool = True,
        resource_profile: ResourceProfile | None = None,
        memory_db_path: str = "anne.db",
    ) -> None:
        self.memory = memory or FractalMemory(memory_db_path)
        self.pipeline = pipeline or AnnePipeline(
            memory=self.memory,
            anla_enabled=anla_enabled,
            fail_fast_enabled=fail_fast_enabled,
        )
        self.resource_profile = resource_profile or ResourceProfile.minimal()
        self.orchestrator = CognitiveOrchestrator(
            self.pipeline,
            resource_profile=self.resource_profile,
        )
        self.character_integrity = CharacterIntegrityGate()

    def run(
        self,
        raw_input: str,
        claim: str | None = None,
        parties: Sequence[Consciousness] | None = None,
        hypothesis: Hypothesis | None = None,
        probability: float = 0.7,
    ) -> DecisionResult:
        parties = list(parties) if parties else [Consciousness(id="user")]
        text_claim = claim if claim is not None else raw_input
        hyp = hypothesis or Hypothesis(
            id=f"h_{uuid4().hex[:12]}",
            topic=text_claim[:48],
            claim=text_claim,
            probability=probability,
            source="decision_loop",
        )
        ff, state = self.pipeline.run_with_fail_fast(raw_input, parties, hyp)
        if not ff.passed:
            return DecisionResult(
                "ABORTED",
                "FAIL_FAST",
                "HALT",
                {
                    "verdict": "FAIL_FAST",
                    "action": "HALT",
                    "reason": ff.reason,
                    "rule_id": ff.rule_id,
                },
                fail_fast=ff.as_dict(),
                reason=ff.reason,
            )
        assert state is not None
        out = state.output or {}
        verdict = out.get("verdict") or state.action or "UNKNOWN"
        action = out.get("action") or ("HALT" if verdict == "REDDET" else "UNKNOWN")
        aborted = verdict in {"REDDET", "FAIL_FAST"} or action == "HALT"
        if verdict == "AYRI_ÇÖZÜM":
            aborted = False
        ethic_total = state.ethic_score.total if state.ethic_score else None
        anla_score = state.context_map.get("anla_score")

        ethic = state.ethic_score
        goodness = ethic.goodness if ethic else 0.0
        equality = ethic.equality if ethic else 0.0
        evidence_available = state.evidence_count > 0 or state.evidence_status in {
            "available",
            "conflicting",
            "unverified",
        }
        contradiction = state.evidence_status == "conflicting" or bool(state.low_prob_preserved)
        character = self.character_integrity.assess(
            probability=hyp.probability,
            goodness=goodness,
            equality=equality,
            evidence_verified=state.evidence_verified,
            evidence_available=evidence_available,
            contradiction=contradiction,
            negative_character_risk=False,
        )
        state.character_integrity = character
        state.output["character_integrity"] = character.as_dict()

        if character.quarantined:
            state.output["learning"] = "QUARANTINED"

        return DecisionResult(
            "ABORTED" if aborted else "EXECUTED",
            str(verdict),
            str(action),
            state.output,
            ff.as_dict(),
            anla_score if isinstance(anla_score, (int, float)) else None,
            ethic_total,
            state,
            str(out.get("reason") or out.get("note") or ""),
            character.as_dict(),
        )

    def run_cognitive(
        self,
        raw_input: str,
        *,
        parties: Sequence[Consciousness] | None = None,
        task_mode: TaskMode = TaskMode.GENERAL,
        seed: int | None = None,
    ) -> OrchestrationResult:
        """Run the Phase 1a executive path with MITOS proposal/ANNE selection."""
        return self.orchestrator.run(
            raw_input,
            parties=parties,
            task_mode=task_mode,
            seed=seed,
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
    ) -> FractalResult:
        """Run bounded frame → branch → reframe recursion through ANNE gates."""
        parties = list(parties) if parties else [Consciousness(id="user")]
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
        ).run(
            raw_input,
            hyp,
            parties=parties,
            task_mode=task_mode,
        )
