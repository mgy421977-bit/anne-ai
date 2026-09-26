# Contextual Memory V1 — Phase 1 Foundation

**Status:** Implemented in Phase 1. Runtime integration is deferred to Phase 2.

## Scope

Contextual Memory V1 is an additive, project-scoped persistence layer on ANNE's existing SQLite foundation. It reuses `connect_memory()` and `RedactingConnection`; it does not replace `FractalMemory` and it does not create a second database.

The service is explicit: it does not automatically ingest every conversation and it does not execute actions.

## Service

Module: `src/anne/memory/contextual_memory.py`

Primary API: `ContextualMemoryService`

- `create_project()` / `create_session()` / `close_session()`
- `record_record()` for typed contextual records
- `record_event()`
- `save_state()` / `checkpoint_state()`
- `get_current_state()` / `get_previous_state()`
- `record_decision()` / decision supersession
- `record_reason()` / `record_hypothesis()` / `record_failure()`
- `record_evidence_ref()`
- `add_relation()`
- `add_unresolved_item()` / `resolve_unresolved_item()`
- `add_next_action()` / `complete_next_action()`
- `load_project_context()`

The canonical cognitive runtime is intentionally unchanged in Phase 1. `AnneAgent`, `AnneRuntime`, `DecisionLoop`, `CognitiveOrchestrator`, and `AnnePipeline` do not automatically read or write this service yet.

## Schema and migration

`memory_schema_version` records the applied schema version. Version 1 is idempotently applied using `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`. Existing FractalMemory tables remain intact and existing databases open successfully.

Contextual tables:

- `contextual_projects`
- `contextual_sessions`
- `contextual_records`
- `contextual_events`
- `contextual_states`
- `contextual_decisions`
- `contextual_evidence_refs`
- `contextual_relations`
- `contextual_unresolved_items`
- `contextual_next_actions`

Identity, scope, type/status and timestamps are structured columns. Flexible payloads are JSON fields. Contextual writes use parameterized SQL and inherit the existing redaction boundary.

## State and decision semantics

State transitions are append-oriented. `checkpoint_state()` atomically:

1. marks the prior current state `SUPERSEDED`,
2. inserts the new `CURRENT` state,
3. appends a `STATE_TRANSITION` event.

The prior state is retained and linked by `previous_state_id`. Decisions use analogous `ACTIVE`/`SUPERSEDED` status and retain superseded decision records.

## Evidence boundary

> **MEMORY ≠ EVIDENCE**
>
> **MEMORY ≠ VERIFICATION**

`record_evidence_ref()` stores a reference to an independently established verifier result. It never calls `ClaimVerifier`, `EvidenceGate`, or any verification service. A stored `verifier_status=verified` is historical provenance/context; it does not create `EvidenceStatus.AVAILABLE` or bypass current verification.

Context reconstruction does not mutate `EvidenceStatus`, `FactualStatus`, `EvidenceGate`, or `AgencyGate`.

## Context reconstruction

`load_project_context(project_id, session_id=None)` returns deterministic structured data:

- project
- current state
- most recent superseded/previous state
- recent events, newest first
- active decisions, active first then newest
- hypotheses
- evidence references
- open/blocked unresolved items
- pending/in-progress/blocked next actions
- contextual failures

All results are explicitly project-scoped. Relations reject source/target records owned by another project. Session-specific queries filter by the requested session; project-level queries may aggregate sessions.

## Phase 1 vs Phase 2

### Implemented in Phase 1

- SQLite schema and version table
- project/session identity
- typed contextual records
- append-oriented events
- state snapshots and supersession
- contextual decisions and supersession
- hypothesis/reason/failure records
- evidence references with verifier status preservation
- project-scoped relations
- unresolved item lifecycle
- next action lifecycle
- deterministic context reconstruction
- atomic state checkpoint transaction
- isolation, restart, rollback and evidence-boundary tests

### Deferred to Phase 2

- Integration with the canonical cognitive runtime
- Automatic conversation/event capture
- Automatic project/session inference
- Runtime use of reconstructed context
- Any action execution based on next-action records
- Retention, archival and compaction policy
- Stronger multi-process/concurrent SQLite deployment
- Semantic/vector/graph retrieval

Contextual Memory reconstructs project context; it does not establish factual truth, consciousness, AGI, human-like memory, autonomous learning, or general causal intelligence.
