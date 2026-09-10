# ANNE Agency Gate — Implementation Contract

## Purpose

This document connects the Agency Approval Protocol to the runtime architecture. It defines the required control boundary before ANNE can modify external state.

## Core rule

> ANNE may think, investigate, learn, plan and propose autonomously. An action that changes external or durable state requires explicit user approval before execution.

## Flow

```text
User request
    ↓
ANNE / MITOS
    ↓
Task decomposition + context
    ↓
Specialist AI / tools
    ↓
Evidence + comparison + cognitive evaluation
    ↓
Proposed action
    ↓
AGENCY GATE
    ├── Read-only / internal reasoning → may continue within policy
    └── External or durable change → approval required
                              ↓
                    User reviews proposal
                    ├── APPROVE → execute exact scope
                    ├── REJECT  → do not execute
                    └── MODIFY  → revise proposal and ask again
                              ↓
                         Result + evidence
                              ↓
                       ANNE learns / records
```

## Proposal contract

Before an approval-gated action, ANNE should present, in human-readable form:

1. **Action** — exactly what will change.
2. **Reason** — why the change is proposed.
3. **Evidence** — observations, tests, references or model outputs supporting it.
4. **Scope** — files, services, repositories, records or other resources affected.
5. **Risk** — expected failure modes and impact.
6. **Validation** — tests/checks that will be run before or after execution.
7. **Rollback** — how the change can be reversed, when possible.
8. **Authority** — why ANNE is allowed to request this action.

The approval must be explicit. Silence, timeout, ambiguity or an unavailable user is **not** approval.

## Protected actions

The gate applies to, at minimum:

- modifying or deleting repository files;
- creating commits, branches or pull requests that represent a requested change;
- modifying Vitavolt or other deployed/public content;
- writing outside an explicitly authorized local workspace;
- sending external data or messages;
- changing tool permissions or agent authority;
- creating or materially changing persistent agents;
- changing runtime configuration with external impact;
- any action whose consequences cannot be considered purely internal/read-only.

## Safe-by-default local workspace

A local installation may use an explicitly configured workspace such as `E:\ANNE\`. The workspace is an execution boundary, not unrestricted filesystem authority. Access outside the boundary must be separately authorized and, where it creates durable/external effects, approval-gated.

## MITOS boundary

MITOS manages cognitive exploration and can propose decomposition, questions, specialist selection, prompts, hypotheses and actions. MITOS does **not** receive implicit authority to execute external changes merely because it generated the plan.

## Learning after execution

After an approved action, ANNE should record the proposal, approval decision, execution result, evidence and outcome. A successful execution is an experience; it is not automatically proof that the underlying strategy is generally correct. Reusable strategy claims require appropriate tests or benchmarks.

## Implementation status

This document is an implementation contract. The repository must not claim full enforcement merely because this policy exists. Runtime enforcement, tests, UI approval handling, audit records and connector-specific authorization must be implemented and verified before the corresponding capability is marked `IMPLEMENTED`.

## Research principle

The Agency Gate separates **cognitive autonomy** from **action authority**:

> Think broadly. Propose clearly. Act only within explicit authority.
