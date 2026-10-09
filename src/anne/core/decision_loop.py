"""DecisionLoop — mandatory facade over ANNE's guarded cognitive paths."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from anne.core.adaptive_resource_planner import AdaptiveResourcePlanner, ResourceDecision
from anne.core.cognitive_orchestrator import CognitiveOrchestrator, OrchestrationResult
from anne.core.cognitive_state import CognitiveState, Consciousness, Hypothesis
from anne.core.compute_router import ComputeEnvironment, ComputeRouter, ExecutionMode
from anne.core.fractal_loop import FractalBudget, FractalResult, FractalThinkingLoop
from anne.core.pipeline import AnnePipeline
from anne.core.resource_negotiator import ResourceNegotiator
from anne.core.resource_optimizer import ResourceOptimizer, SystemResourceProbe
from anne.core.resource_profile import ResourceProfile
from anne.core.trace import CycleTrace, trace_from_runtime
from anne.core.verification import ClaimVerifier
from anne.core.windows_execution import WindowsExecutionAdapter
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
        }


class DecisionLoop:
    """Single entry point for ANNE's guarded cognitive runtime."""

    def __init__(
        self,
        memory: FractalMemory | None = None,
        pipeline: AnnePipeline | None = None,
        anla_enabled: bool = True,
        fail_fast_enabled: bool = True,
        resource_profile: ResourceProfile | None = None,
        memory_db_path: str = "anne.db",
        claim_verifier: ClaimVerifier | None = None,
        execution_environments: Sequence[ComputeEnvironment] | None = None,
    ) -> None:
        self.memory = memory or FractalMemory(memory_db_path)
        self.pipeline = pipeline or AnnePipeline(
            memory=self.memory,
            anla_enabled=anla_enabled,
            fail_fast_enabled=fail_fast_enabled,
            claim_verifier=claim_verifier,
        )
        self.resource_profile = resource_profile or ResourceProfile.minimal()
        self.resource_planner = AdaptiveResourcePlanner()
        self.resource_optimizer = ResourceOptimizer()
        self.resource_probe = SystemResourceProbe()
        self.resource_negotiator = ResourceNegotiator()
        self.windows_execution = WindowsExecutionAdapter()
        self.compute_router = ComputeRouter()
        self._explicit_resource_profile = resource_profile is not None
        self._experience_history: tuple[dict[str, Any], ...] = ()
        self._experience_history_limit = 64
        self.execution_environments = (
            tuple(execution_environments)
            if execution_environments is not None
            else (ComputeEnvironment("local-default", ExecutionMode.LOCAL, capacity=1),)
        )
        self.orchestrator = CognitiveOrchestrator(
            self.pipeline,
            resource_profile=self.resource_profile,
        )

    @staticmethod
    def _resource_payload(
        decision: ResourceDecision,
        route: Any,
        negotiation: Any,
        optimization: Any,
        execution_plan: Any,
    ) -> dict[str, Any]:
        environment = route.selected_environment
        return {
            "execution": decision.execution,
            "basis": decision.basis,
            "reason": decision.reason,
            "estimated_complexity": decision.estimated_complexity,
            "minimum_sufficient_capacity": decision.minimum_sufficient_capacity,
            "experience_profile": {
                "observation_count": decision.experience_profile.observation_count,
                "resource_failure_count": decision.experience_profile.resource_failure_count,
                "reusable_count": decision.experience_profile.reusable_count,
                "success_count": decision.experience_profile.success_count,
                "failure_count": decision.experience_profile.failure_count,
                "success_rate": decision.experience_profile.success_rate,
            },
            "profile": {
                "substrate": decision.profile.substrate.value,
                "cpu_units": decision.profile.cpu_units,
                "memory_units": decision.profile.memory_units,
                "reasoning_budget": decision.profile.reasoning_budget,
                "max_mitos_candidates": decision.profile.max_mitos_candidates,
                "max_fractal_depth": decision.profile.max_fractal_depth,
                "max_iterations": decision.profile.max_iterations,
            },
            "optimization": {
                "status": optimization.status,
                "requested_capacity": optimization.requested_capacity,
                "optimized_capacity": optimization.optimized_capacity,
                "reason": optimization.reason,
                "host": {
                    "cpu_count": optimization.snapshot.cpu_count,
                    "cpu_utilization": optimization.snapshot.cpu_utilization,
                    "memory_total_bytes": optimization.snapshot.memory_total_bytes,
                    "memory_available_bytes": optimization.snapshot.memory_available_bytes,
                    "gpu_count": optimization.snapshot.gpu_count,
                    "gpu_utilization": optimization.snapshot.gpu_utilization,
                    "os_present": optimization.snapshot.os_present,
                },
            },
            "negotiation": {
                "status": negotiation.status,
                "platform": negotiation.platform_name,
                "ownership": negotiation.ownership,
                "shared_driver_boundary": negotiation.shared_driver_boundary,
                "shared_subsystems": list(negotiation.shared_subsystems),
                "reason": negotiation.reason,
            },
            "windows_execution": {
                "status": execution_plan.status,
                "requested_capacity": execution_plan.requested_capacity,
                "priority": execution_plan.priority,
                "affinity_mask": execution_plan.affinity_mask,
                "requires_authorization": execution_plan.requires_authorization,
                "reason": execution_plan.reason,
            },
            "route": {
                "status": route.status,
                "reason": route.reason,
                "required_capacity": route.required_capacity,
                "environment_id": environment.id if environment else None,
                "execution_mode": environment.mode.value if environment else None,
            },
        }

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
        mitos_outcomes: Sequence[Any] | None = None,
        mitos_failure_classes: dict[str, str] | None = None,
    ) -> DecisionResult:
        """Plan resources first, then run the canonical cognitive path."""
        resource_decision = self.resource_planner.plan(
            raw_input,
            experiences=self._experience_history,
            mitos_outcomes=tuple(mitos_outcomes or ()),
            mitos_failure_classes=mitos_failure_classes,
            baseline=self.resource_profile if self._explicit_resource_profile else None,
        )
        runtime_snapshot = self.resource_probe.snapshot()
        optimization = self.resource_optimizer.optimize(
            resource_decision.profile,
            runtime_snapshot,
        )
        optimized_profile = self.resource_optimizer.apply(
            resource_decision.profile,
            optimization,
        )
        if optimized_profile != resource_decision.profile:
            resource_decision = ResourceDecision(
                profile=optimized_profile,
                execution=resource_decision.execution,
                basis=resource_decision.basis,
                reason=resource_decision.reason + "; " + optimization.reason,
                estimated_complexity=resource_decision.estimated_complexity,
                minimum_sufficient_capacity=resource_decision.minimum_sufficient_capacity,
                experience_profile=resource_decision.experience_profile,
            )

        self.resource_profile = resource_decision.profile
        self.orchestrator.resource_profile = resource_decision.profile
        self.orchestrator.candidate_batch_size = (
            resource_decision.profile.max_mitos_candidates
        )
        negotiation = self.resource_negotiator.negotiate(
            resource_decision.profile,
            optimization,
            runtime_snapshot,
        )
        execution_plan = self.windows_execution.plan(
            negotiation.effective_profile,
            background=False,
        )
        route = self.compute_router.route(
            negotiation.effective_profile,
            self.execution_environments,
        )

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

        resource_payload = self._resource_payload(
            resource_decision,
            route,
            negotiation,
            optimization,
            execution_plan,
        )
        if not result.fail_fast.passed:
            fail_output = {
                "verdict": "FAIL_FAST",
                "action": "HALT",
                "reason": result.fail_fast.reason,
                "rule_id": result.fail_fast.rule_id,
                "resource_decision": resource_payload,
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
                "ABORTED", "FAIL_FAST", "HALT", fail_output,
                fail_fast=result.fail_fast.as_dict(),
                reason=result.fail_fast.reason, trace=trace,
            )

        state = result.state
        out = dict(state.output) if state is not None else {}
        out["resource_decision"] = resource_payload
        verdict = out.get("verdict") or (state.action if state else None) or "UNKNOWN"
        action = out.get("action") or ("HALT" if verdict == "REDDET" else "UNKNOWN")
        aborted = (
            result.status != "EXECUTED"
            or verdict in {"REDDET", "FAIL_FAST", "ABSTAIN", "REVIEW"}
            or action in {"HALT", "REVIEW"}
        )
        if verdict == "AYRI_ÇÖZÜM":
            aborted = False

        if result.status == "EXECUTED":
            failure_class = ""
            outcome = "SUCCESS" if not aborted else verdict
        else:
            failure_class = str(out.get("failure_class") or "unknown")
            outcome = str(verdict or result.status)
        self._experience_history = (
            *self._experience_history,
            {
                "outcome": outcome,
                "failure_class": failure_class,
                "strategy": strategy or "",
                "lesson": str(out.get("reason") or ""),
                "safe_to_reuse": False,
            },
        )[-self._experience_history_limit :]

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
            trace,
        )


    def _prepare_runtime_profile(self, raw_input: str) -> ResourceProfile:
        """Prepare a bounded resource profile for every public execution path."""
        decision = self.resource_planner.plan(
            raw_input,
            experiences=self._experience_history,
            baseline=self.resource_profile if self._explicit_resource_profile else None,
        )
        snapshot = self.resource_probe.snapshot()
        optimization = self.resource_optimizer.optimize(decision.profile, snapshot)
        profile = self.resource_optimizer.apply(decision.profile, optimization)
        negotiation = self.resource_negotiator.negotiate(profile, optimization, snapshot)
        profile = negotiation.effective_profile
        self.resource_profile = profile
        self.orchestrator.resource_profile = profile
        self.orchestrator.candidate_batch_size = profile.max_mitos_candidates
        # Routing is observational: a deferred route never grants permission
        # to execute remotely or provisions additional infrastructure.
        self.compute_router.route(profile, self.execution_environments)
        self.windows_execution.plan(profile, background=False)
        return profile

    def run_cognitive(
        self,
        raw_input: str,
        *,
        parties: Sequence[Consciousness] | None = None,
        task_mode: TaskMode = TaskMode.GENERAL,
        seed: int | None = None,
        verifier: ClaimVerifier | None = None,
    ) -> OrchestrationResult:
        self._prepare_runtime_profile(raw_input)
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
        profile = self._prepare_runtime_profile(raw_input)
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
            resource_profile=profile,
            claim_verifier=verifier,
        ).run(
            raw_input,
            hyp,
            parties=people,
            task_mode=task_mode,
        )


__all__ = ["DecisionLoop", "DecisionResult"]
