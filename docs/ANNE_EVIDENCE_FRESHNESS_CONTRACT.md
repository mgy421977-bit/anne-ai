# ANNE Evidence Freshness Contract

## Purpose

Evidence retrieval time is useful temporal metadata. It is not truth, confidence,
authority, or verification.

Freshness is therefore assessed separately from factual verification:

`RETRIEVED_AT -> REFERENCE_TIME -> FRESHNESS_ASSESSMENT`

The assessment may be **CURRENT**, **AGING**, **STALE**, or **UNKNOWN**.

## Rules

1. The caller supplies an explicit reference time.
2. The caller supplies the temporal policy thresholds.
3. No universal rule such as "24 hours means stale" is embedded in the core.
4. A newer item is not automatically more correct.
5. A stale item is not automatically false.
6. Freshness must not upgrade UNVERIFIED, CONFLICTING, or REFUTED evidence.
7. Freshness must not grant action authority.
8. A retrieval timestamp later than the reference time is **UNKNOWN**, not current.
9. Timestamps must include timezone information.
10. Domain-specific validity windows belong in an explicit caller policy.

## Intended pipeline

The future research pipeline can use the result as one input:

`retrieval -> cache decision -> freshness -> retry/backoff -> source independence -> verification`

Freshness is an input to research strategy, not a substitute for source quality or
independent verification.

## Non-goals

This contract does not decide:

- whether a source is trustworthy;
- whether a claim is true;
- whether two sources are independent;
- whether evidence is sufficient for an action;
- whether a source should be preferred solely because it is newer.

Those decisions remain separate bounded stages.
