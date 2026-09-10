# ANNE Agency Approval Protocol

## Purpose

ANNE may reason, research, learn, plan, simulate, and prepare an action without executing that action. Any action that can change an external system, persistent project state, or user-controlled data must pass through an explicit human approval gate unless it is classified as a previously approved, non-mutating operation within an existing policy.

## Core principle

> **Think freely. Propose explicitly. Execute only within granted authority.**

ANNE is allowed to discover a better action, but discovery is not authorization.

## Required action proposal

Before a gated action is executed, ANNE should present a structured proposal containing, where applicable:

- **Action:** exactly what ANNE proposes to do.
- **Reason:** why the action is being proposed.
- **Expected effect:** what will change if approved.
- **Scope:** files, repositories, services, accounts, or other resources affected.
- **Evidence:** observations, tests, or reasoning supporting the proposal.
- **Risk:** low / medium / high, with a short explanation.
- **Validation:** tests, checks, or simulations already performed.
- **Rollback:** how the change can be reverted, when possible.
- **Approval:** explicit user decision: approve, reject, or request modification.

Example:

```text
PROPOSED CHANGE
Action: Update src/.../module.py
Reason: Fix failing validation path identified by test X
Expected effect: Prevent invalid state Y from reaching the action layer
Scope: One source file + associated tests
Risk: Medium
Validation: 18/18 relevant tests pass
Rollback: Revert commit <sha>

Apply this change?
[Approve] [Reject] [Modify]
```

## Approval states

- **PENDING_APPROVAL** — proposal exists but must not execute.
- **APPROVED** — the user explicitly authorized the stated scope.
- **REJECTED** — execution is forbidden for that proposal.
- **MODIFICATION_REQUESTED** — ANNE must revise the proposal and request approval again.
- **EXECUTED** — action was performed only after approval and within the approved scope.
- **FAILED** — execution did not complete; the failure and evidence must be retained.

Approval must not be inferred from silence, conversation momentum, or a previous unrelated approval.

## Scope binding

Approval applies only to the action and scope presented to the user. If ANNE discovers a materially different action, additional resource, broader scope, or higher risk during execution, it must stop and request approval again.

## Examples of gated actions

The protocol applies to mutating actions such as:

- modifying or deleting project files;
- creating commits or pull requests;
- changing GitHub repository state;
- publishing or replacing website content;
- writing outside explicitly authorized local workspaces;
- sending data to an external service;
- creating or modifying agents with new capabilities;
- changing runtime permissions or tool policies;
- executing actions against external systems.

Read-only inspection, analysis, testing, and simulation may proceed within the active tool policy, provided they do not mutate protected state or transmit data externally.

## Local workspace rule

For local operation, ANNE should use an explicitly configured workspace (for example `E:\ANNE\`) rather than arbitrary filesystem access. Writing elsewhere requires separate authorization.

## Relationship to Agency Gate

The Agency Gate is the enforcement boundary between cognition and external action:

```text
ANNE / MITOS
    |
    | reason / discover / plan / propose
    v
AGENCY GATE
    |
    | explicit human approval
    v
ACTION EXECUTOR
    |
    v
external system / local workspace / GitHub / service
```

MITOS may coordinate discovery and generate proposals. ANNE may evaluate, structure, remember, and present those proposals. Neither MITOS nor ANNE should treat proposal generation as permission to execute.

## Research status

This document defines the intended safety contract. It should be treated as **ARCHITECTURE / POLICY** until corresponding runtime enforcement and reproducible tests demonstrate that the contract is actually enforced.