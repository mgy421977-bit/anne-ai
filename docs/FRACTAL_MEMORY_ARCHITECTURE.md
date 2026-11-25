# Fractal Memory Architecture v2.0

## Purpose and non-goals

FHM v2 provides deterministic, SQLite-backed memory tiers for ANNE. The memory
engine has no LLM dependency. An LLM may propose content, but it cannot mutate
memory integrity, approve a seal, or bypass provenance and lifecycle rules.

FHM is not a claim that a record is permanently true. `SEALED` means that the
record passed the current evidence and approval policy and is retained as an
append-only version.

## Three tiers

- **L1 — Golden Record:** approved, versioned records that may influence future
  decisions. L1 is append-only: records are never overwritten or pruned. A new
  approved version marks the prior version `SUPERSEDED`; a known-invalid record
  may become `REVOKED`.
- **L2 — Synthesis:** cross-checked records assembled from evidence with source
  provenance, source independence and freshness checks.
- **L3 — Raw Inbox:** redacted, time-stamped candidate observations. L3 is the
  landing zone for public web snippets, user notes and unverified inputs.

## ARCH-MGY-26 v1.0 envelope

Each record is represented by the following logical envelope:

```json
{
  "protocol": "ARCH-MGY-26",
  "protocol_version": "1.0",
  "record_id": "mem_<uuid>",
  "memory_tier": "L3",
  "domain": "regulatory_tax",
  "key": "ges_2026_support",
  "payload": {},
  "evidence": [],
  "anne_ai_filter": {
    "truth_confidence": 0.0,
    "source_independence": 0.0,
    "freshness_valid": true,
    "provenance_complete": false,
    "safety_policy": "PASS"
  },
  "lifecycle": {
    "status": "CANDIDATE",
    "created_at": "2026-11-25T00:00:00Z",
    "updated_at": "2026-11-25T00:00:00Z",
    "supersedes": null
  }
}
```

Timestamps are ISO-8601 UTC. Payload hashing uses canonical JSON: UTF-8,
`ensure_ascii=false`, sorted keys and compact separators.

## Evidence and deterministic thresholds

An L3 record can be promoted to L2 only when all conditions hold:

1. At least three evidence rows exist.
2. At least two distinct `independence_group` values exist.
3. Every evidence item has non-empty provenance.
4. Every evidence item is within the domain freshness TTL.
5. No open high-severity conflict exists for the record.

Source authority is a deterministic hint, not proof of truth:

| Source type | Authority |
|---|---:|
| `PRIMARY_OFFICIAL` | 1.00 |
| `PEER_REVIEWED_OR_SPEC` | 0.90 |
| `VERIFIED_INTERNAL` | 0.85 |
| `SECONDARY_WEB` | 0.60 |
| `UNVERIFIED_RAW` | 0.30 |

Domain TTLs are: `market_pricing` 7 days, `regulatory_tax` 30 days,
`operations_project` 90 days, `technical_engineering` 180 days,
`theoretical_axiom` 365 days, and 60 days for unknown domains.

## Seal and approval lifecycle

The fixed default is:

```text
auto_seal = False
human_approval_required = True
```

An L2 record becomes `SEAL_CANDIDATE` only if `truth_confidence >= 0.85`,
`source_independence >= 0.70`, freshness is valid, provenance is complete and
the safety policy passes. It then requires `approve_seal(record_id,
approver_id, approver_role)`. Only `ARCHITECT` and `HUMAN_ADMIN` can approve.
`SYSTEM`, `BOT` and `LLM_AGENT` are rejected and the attempt is audited.

Lifecycle events are append-only in `memory_events`. Record changes and their
event are committed in one SQLite transaction.

## Redaction boundary

Before L3 persistence, ANNE applies existing secret redaction plus deterministic
masking for API keys, bearer tokens, GitHub tokens, Google API keys, valid-looking
T.C. identity numbers, IBANs, email addresses and Turkish mobile numbers. The
stored payload is the masked payload; the original secret is not retained by the
FHM engine.

## Query behavior

`query_fractal()` returns a `FractalQueryResult`, not only a payload. It exposes
records, selected tier, conflicts, freshness, confidence and uncertainty. Tier
priority is used together with freshness and conflict state. An old L1 record is
not presented as unqualified truth when a newer conflicting L2 record exists.

## Reversible archive

L3 pruning is archive-only:

```text
ACTIVE/CANDIDATE → ARCHIVED
ARCHIVED → CANDIDATE (restore)
```

The masked payload and content hash remain available. L1 records are never part
of pruning. Archive and restore transitions are audited.

## SQLite tables

- `memory_records`: envelope, tier, status, version link and content hash.
- `memory_evidence`: source, independence, provenance, freshness and confidence.
- `memory_events`: append-only lifecycle audit events.
- `memory_conflicts`: unresolved or resolved record contradictions.

## Compatibility

The existing `FractalMemory` and `LocalMemory` classes remain available. FHM v2
is exposed as `FractalMemoryEngine` and uses the existing redacting SQLite
connection boundary. Migration is additive; it does not delete old tables.
