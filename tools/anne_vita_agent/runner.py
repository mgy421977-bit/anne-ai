"""Bounded local task runner: ANNE assessment + AgencyGate + allowlisted VITA action."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol

from anne.core.agency_gate import ActionDecision, ActionProposal, AgencyGate
from .vita_adapter import VitaSolarRequest


class VitaAdapter(Protocol):
    def calculate_ges(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class LocalAgent:
    """Execute at most one explicitly allowlisted action per request.

    The first MVP accepts structured JSON tasks. It does not infer shell commands,
    write source code, browse the network, or publish changes.
    """

    def __init__(
        self,
        *,
        workspace: str | Path,
        vita_adapter: VitaAdapter,
        anne_runtime: Any,
        agency_gate: AgencyGate | None = None,
    ) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        if not self.workspace.is_dir():
            raise ValueError("workspace must be a directory")
        self.vita_adapter = vita_adapter
        self.anne_runtime = anne_runtime
        self.agency_gate = agency_gate or AgencyGate()

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(task, dict):
            raise ValueError("task must be a JSON object")
        if task.get("action") != "vita.ges_precheck":
            return {
                "status": "DENIED",
                "reason": "action_not_allowlisted",
                "allowed_actions": ["vita.ges_precheck"],
            }
        inputs = task.get("input")
        if not isinstance(inputs, dict):
            raise ValueError("task.input must be a JSON object")
        # Validate and normalize before invoking ANNE or any execution adapter.
        validated_inputs = asdict(VitaSolarRequest.from_mapping(inputs))

        summary = (
            "Perform a read-only, preliminary VITA solar feasibility calculation. "
            f"Location={validated_inputs['location']}; "
            f"roof_area_m2={validated_inputs['roof_area_m2']}; "
            f"daily_consumption_kwh={validated_inputs['daily_consumption_kwh']}."
        )
        # ANNE provides a cognitive trace; it is not treated as proof of engineering truth.
        anne_result = self.anne_runtime.run_cognitive(summary)
        anne_status = str(getattr(anne_result, "status", "UNKNOWN")).upper()
        anne_reason = str(getattr(anne_result, "reason", ""))

        if anne_status != "EXECUTED":
            return {
                "status": "BLOCKED_BY_ANNE",
                "anne": {"status": anne_status, "reason": anne_reason},
                "reason": "ANNE did not return the explicit EXECUTED status; VITA was not invoked.",
            }

        proposal = ActionProposal(
            action="vita.ges_precheck",
            target="VITA-Engine SolarEngine.calculate_ges",
            reversible=True,
            risk=0.1,
            provenance=("validated-structured-task", "local-vita-adapter"),
            authority_required=False,
            evidence_required=False,
            side_effect=False,
            human_review_required=False,
        )
        authorization = self.agency_gate.authorize(
            proposal,
            safety_allowed=True,
            human_review_required=False,
        )
        if authorization.decision is not ActionDecision.ALLOW:
            return {
                "status": "DENIED_BY_AGENCY_GATE",
                "agency_gate": {
                    "decision": authorization.decision.value,
                    "reason": authorization.reason,
                },
            }

        vita_result = self.vita_adapter.calculate_ges(validated_inputs)
        trace = getattr(anne_result, "stage_trace", ())
        if not trace:
            trace = getattr(anne_result, "trace", ())
        return {
            "status": "COMPLETED",
            "task_id": "vita.ges_precheck",
            "anne": {
                "status": anne_status,
                "reason": anne_reason,
                "trace": list(trace) if isinstance(trace, (tuple, list)) else [],
                "note": "Cognitive assessment is not an engineering verification.",
            },
            "agency_gate": {
                "decision": authorization.decision.value,
                "reason": authorization.reason,
                "policy_version": authorization.policy_version,
            },
            "vita": vita_result,
            "sandbox": {
                "mode": "docker-restricted-container",
                "network": "disabled",
                "vita_mount": "read-only",
                "arbitrary_code_execution": False,
                "workspace": str(self.workspace),
            },
        }


def build_default_agent(vita_root: str | Path, workspace: str | Path) -> LocalAgent:
    """Build ANNE with its memory database inside the chosen workspace."""
    from anne.core.decision_loop import DecisionLoop
    from anne.runtime import AnneRuntime
    from .vita_adapter import DockerVitaAdapter

    workspace_path = Path(workspace).expanduser().resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    runtime = AnneRuntime(
        decision_loop=DecisionLoop(memory_db_path=str(workspace_path / "anne-memory.db"))
    )
    return LocalAgent(
        workspace=workspace_path,
        vita_adapter=DockerVitaAdapter(vita_root),
        anne_runtime=runtime,
    )
