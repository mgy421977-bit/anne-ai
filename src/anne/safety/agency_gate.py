"""Approval boundary for ANNE external and durable actions.

The gate deliberately separates cognitive autonomy from action authority.
Planning and proposal generation can happen upstream (including MITOS),
but an external/durable action must carry an explicit approval before an
executor is allowed to perform it.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    PENDING = "pending"


@dataclass(frozen=True)
class ActionProposal:
    """Human-reviewable description of a proposed action."""

    action: str
    reason: str
    scope: str
    risk: str
    evidence: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    rollback: str = ""
    authority: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalRecord:
    proposal: ActionProposal
    decision: ApprovalDecision = ApprovalDecision.PENDING
    note: str = ""


class AgencyGate:
    """Default-deny action gate.

    The gate is intentionally small: it does not decide whether a proposal
    is intellectually good. It decides whether execution has explicit user
    authority. A real executor should require an approved record immediately
    before performing the corresponding action.
    """

    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}

    def propose(self, proposal_id: str, proposal: ActionProposal) -> ApprovalRecord:
        if not proposal_id:
            raise ValueError("proposal_id is required")
        if proposal_id in self._records:
            raise ValueError(f"proposal already exists: {proposal_id}")
        record = ApprovalRecord(proposal=proposal)
        self._records[proposal_id] = record
        return record

    def decide(
        self,
        proposal_id: str,
        decision: ApprovalDecision,
        note: str = "",
    ) -> ApprovalRecord:
        record = self._records[proposal_id]
        if decision is ApprovalDecision.PENDING:
            raise ValueError("pending is not a user decision")
        record.decision = decision
        record.note = note
        return record

    def can_execute(self, proposal_id: str) -> bool:
        """Return True only after an explicit approval decision."""

        record = self._records.get(proposal_id)
        return record is not None and record.decision is ApprovalDecision.APPROVE

    def require_approval(self, proposal_id: str) -> None:
        """Raise unless the exact proposal has explicit approval."""

        if not self.can_execute(proposal_id):
            raise PermissionError(
                "Agency Gate: explicit user approval is required before execution"
            )

    def get_record(self, proposal_id: str) -> ApprovalRecord:
        return self._records[proposal_id]
