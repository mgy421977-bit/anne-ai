# ANNE Canonical Trace Contract

**Status:** Phase 1 foundation
**Schema:** `1.1`

The canonical trace is an observability contract for one bounded cognitive cycle. It is provider-independent and does not grant authority.

## Invariants

1. A trace has an explicit cycle id, status, and schema version.
2. Retry counts are non-negative.
3. Parent and lineage identifiers are explicit.
4. Evidence and verification are recorded separately from confidence.
5. Joint inference and derived hypotheses are recorded separately from verification and authority.
6. Agency results are recorded separately from cognitive decisions.
7. Provenance is explicit and never inferred from text similarity.
8. Serialization is deterministic for replay and benchmark comparison.
9. The trace cannot bypass FailFast, Evidence Gate, provenance verification, or Agency Gate.

## Canonical sections

- `cycle_id`: unique cycle identifier.
- `parent_cycle_id`, `lineage`: bounded retry/reframe lineage.
- `stage_trace`: observed stage execution order.
- `intent`: explicit intent/routing information.
- `hypotheses`: candidate records when available.
- `evidence`: evidence records when available; evidence is not truth.
- `joint_inferences`: explicit derived claims and their premise/source-independence observations; inference is not truth.
- `derived_hypotheses`: bounded follow-up research targets produced from eligible joint inferences; proposals are not decisions.
- `verification`: verification status, sources, reason and evidence state.
- `decision`: observed verdict/action/reason.
- `agency`: Agency Gate decision and human-review requirement.
- `provenance`: explicit provenance graph/dependency references.
- `learning`: failure/retry/experience signals.
- `metrics`: latency/resource counters.
- `errors`: structured failures.

## Versioning

Schema `1.1` adds `joint_inferences` and `derived_hypotheses` as additive observability fields. Older serialized traces remain readable because missing fields default to empty tuples.

These fields are intentionally observational: recording a derived inference does not verify it, recording source-family diversity does not prove independence, and recording a proposed hypothesis does not authorize research or action.

## Fast activation path

This contract is introduced without changing decision semantics. The existing runtime adapter can copy explicit inference observations into the trace, after which the same trace can feed metacognition and experience-learning components.

## Bounded autonomous improvement

Under explicit human directives, ANNE may research public sources, compare evidence, propose implementation changes, validate them in isolation, and prepare reviewable changes. Research remains evidence rather than authority. ANNE must not self-certify correctness, weaken safety or agency gates, merge its own changes, or silently change authorization policy.
