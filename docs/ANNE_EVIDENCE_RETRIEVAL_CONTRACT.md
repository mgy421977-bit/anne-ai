# ANNE Evidence Retrieval Metadata Contract

## Purpose

ANNE records when an evidence item was retrieved so later research, re-evaluation, and observability can distinguish the existence of evidence from its temporal context.

## Contract

Each EvidenceItem carries `retrieved_at` as an ISO-8601 timestamp.

The runtime preserves that timestamp in EvidenceLedgerEntry and serialized research output.

## Epistemic boundary

`retrieved_at` is metadata, not a truth signal.

A newer item is not automatically more correct than an older item. A timestamp must not upgrade:

- UNVERIFIED to VERIFIED
- CONFLICTING to VERIFIED
- REFUTED to VERIFIED
- authority or agency permissions

Freshness policy, when introduced, must remain separate from factual verification and must be explicit about its reference time and domain-specific validity window.

## Missing or malformed timestamps

New evidence receives the current UTC retrieval timestamp when one is not supplied. Explicit timestamps must be valid ISO-8601 values. Malformed timestamps fail closed.

## Future work

A future reliability layer may add explicit freshness classification, source independence, timeout/retry/backoff telemetry, and cache metadata. Those signals must remain observational until an explicit verification policy uses them.
