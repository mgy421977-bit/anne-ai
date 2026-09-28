# ANNE Canonical Trace Contract

**Status:** Phase 1 foundation
**Schema:** `1.0`

The canonical trace is an observability contract for one bounded cognitive cycle. It is provider-independent and does not grant authority.

## Invariants

1. A trace has an explicit cycle id, status, and schema version.
2. Retry counts are non-negative.
3. Parent and lineage identifiers are explicit.
4. Evidence and verification are recorded separately from confidence.
5. Agency results are recorded separately from cognitive decisions.
6. Provenance is explicit and never inferred from text similarity.
7. Serialization is deterministic for replay and benchmark comparison.
8. The trace cannot bypass FailFast, Evidence Gate, provenance verification, or Agency Gate.

## Canonical sections

- `cycle_id`: unique cycle identifier.
- `parent_cycle_id`, `lineage`: bounded retry/reframe lineage.
- `stage_trace`: observed stage execution order.
- `intent`: explicit intent/routing information.
- `hypotheses`: candidate records when available.
- `evidence`: evidence records when available; evidence is not truth.
- `verification`: verification status, sources, reason and evidence state.
- `decision`: observed verdict/action/reason.
- `agency`: Agency Gate decision and human-review requirement.
- `provenance`: explicit provenance graph/dependency references.
- `learning`: failure/retry/experience signals.
- `metrics`: latency/resource counters.
- `errors`: structured failures.

## Fast activation path

This contract is introduced without changing decision semantics. The next integration step is to emit one canonical trace from the existing `CognitiveOrchestrator`/`DecisionLoop` path, then feed the same trace into metacognition and experience-learning components.

## Bounded autonomous improvement

Under explicit human directives, ANNE may research public sources, compare evidence, propose implementation changes, validate them in isolation, and prepare reviewable changes. Research remains evidence rather than authority. ANNE must not self-certify correctness, weaken safety or agency gates, merge its own changes, or silently change authorization policy.
