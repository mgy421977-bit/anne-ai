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
from anne.core.trace import CycleTrace, trace_from_runtime
from anne.learning.context_fingerprint import ExplicitContextFingerprint
from anne.learning.experience_learning import Experience
from anne.learning.research_cognitive_loop import (
    ResearchCognitiveLoop,
    ResearchCognitiveState,
)
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
    trace: CycleTrace | None = None
    research_state: ResearchCognitiveState | None = None

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
            "trace": self.trace.as_dict() if self.trace is not None else None,
            "research": (
                {
                    "action": self.research_state.decision.action,
                    "reason": self.research_state.decision.reason,
                    "research_allowed": self.research_state.decision.research_allowed,
                    "questions": ResearchCognitiveLoop.next_research_questions(
                        self.research_state
                    ),
                }
                if self.research_state is not None
                else None
            ),
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
        self.research_loop = ResearchCognitiveLoop(memory=self.memory)
        self._experience_history: tuple[Experience, ...] = ()
        self._experience_history_limit = 64

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
        learning_context: dict[str, Any] | None = None,
        strategy: str | None = None,
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
            preferred_strategy=strategy,
        )
        if not result.fail_fast.passed:
            fail_output = {
                "verdict": "FAIL_FAST",
                "action": "HALT",
                "reason": result.fail_fast.reason,
                "rule_id": result.fail_fast.rule_id,
            }
            trace = trace_from_runtime(
                cycle_id=result.lineage[-1] if result.lineage else f"or_{uuid4().hex[:12]}",
                status="ABORTED",
                stage_trace=result.stage_trace,
                stop_reason=result.stop_reason or "fail_fast",
                retry_count=result.retry_count,
                lineage=result.lineage or (),
                output=fail_output,
                learning_context=learning_context,
                strategy=strategy,
            )
            return DecisionResult(
                "ABORTED",
                "FAIL_FAST",
                "HALT",
                fail_output,
                fail_fast=result.fail_fast.as_dict(),
                reason=result.fail_fast.reason,
                trace=trace,
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
        trace = trace_from_runtime(
            cycle_id=result.lineage[-1] if result.lineage else f"or_{uuid4().hex[:12]}",
            status=result.status,
            stage_trace=result.stage_trace,
            stop_reason=result.stop_reason,
            retry_count=result.retry_count,
            lineage=result.lineage or (),
            output=out,
            context=state.context_map if state is not None else None,
            learning_context=learning_context,
            strategy=strategy,
        )
        # Historical experience is observational only. Reuse is explicitly
        # scoped to the exact runtime context recorded for this cycle; an
        # empty context never imports history from another task.
        explicit_context = ExplicitContextFingerprint.from_context(
            trace.learning.get("context", {})
            if isinstance(trace.learning, dict)
            else {}
        )
        current_experience = getattr(self, "_experience_history", ())
        history_limit = getattr(self, "_experience_history_limit", 64)
        if explicit_context.key or explicit_context.conditions:
            memory = getattr(self, "memory", None)
            persisted = (
                memory.get_experience_observations(
                    context_key=explicit_context.key,
                    context_conditions=explicit_context.conditions,
                    limit=history_limit,
                )
                if memory is not None
                else ()
            )
            persisted_experiences = tuple(
                Experience(**item) for item in reversed(persisted)
            )
            in_process = tuple(
                item
                for item in current_experience
                if item.context_key == explicit_context.key
                and item.context_conditions == explicit_context.conditions
            )
            combined = persisted_experiences + in_process
            deduped: dict[str, Experience] = {}
            for item in combined:
                deduped[item.source_cycle_id] = item
            prior_experiences = tuple(deduped.values())[-history_limit:]
        else:
            prior_experiences = ()

        research_state = self.research_loop.initialize(
            raw_input,
            completed_trace=trace,
            strategy=strategy or "research",
            prior_experiences=prior_experiences,
        )
        if research_state.adaptive_learning is not None:
            observed = research_state.adaptive_learning.experience
            self._experience_history = (
                *current_experience,
                observed,
            )[-history_limit :]
            memory = getattr(self, "memory", None)
            if memory is not None and (
                observed.context_key or observed.context_conditions
            ):
                memory.save_experience_observation(
                    source_cycle_id=observed.source_cycle_id,
                    outcome=observed.outcome,
                    failure_class=observed.failure_class,
                    strategy=observed.strategy,
                    lesson=observed.lesson,
                    safe_to_reuse=observed.safe_to_reuse,
                    factual_status=observed.factual_status,
                    context_key=observed.context_key,
                    context_conditions=observed.context_conditions,
                    parent_cycle_id=observed.parent_cycle_id,
                    lineage=observed.lineage,
                )
        enriched_trace = (
            research_state.adaptive_learning.trace
            if research_state.adaptive_learning is not None
            else trace
        )
        next_step = research_state.decision.action
        final_status = "ABORTED" if aborted else "EXECUTED"
        final_verdict = str(verdict)
        final_action = str(action)
        final_reason = str(out.get("reason") or out.get("note") or "")

        # Metacognitive guidance is a bounded post-cycle control signal.
        # It may stop a result from being treated as final, but it never
        # grants execution authority and it never executes research itself.
        if not aborted and next_step in {"RESEARCH", "REVIEW"}:
            original_output = dict(out)
            out = {
                **original_output,
                "original_output": original_output,
                "verdict": next_step,
                "action": next_step,
                "reason": research_state.decision.reason,
                "metacognitive_next_step": next_step,
                "research_questions": ResearchCognitiveLoop.next_research_questions(
                    research_state
                ),
            }
            final_status = "BOUNDED"
            final_verdict = next_step
            final_action = next_step
            final_reason = research_state.decision.reason

        return DecisionResult(
            final_status,
            final_verdict,
            final_action,
            out,
            result.fail_fast.as_dict(),
            anla_score if isinstance(anla_score, (int, float)) else None,
            ethic_total,
            state,
            final_reason,
            enriched_trace,
            research_state,
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
