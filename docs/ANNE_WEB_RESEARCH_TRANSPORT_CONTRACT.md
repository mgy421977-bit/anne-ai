# ANNE Web Research Transport Contract

## Purpose

This contract defines bounded transport behavior for public-web research:

cache -> retry -> backoff -> retrieval

It separates transport reliability from factual reliability.

## Cache

A cache policy explicitly defines:

- maximum age (ttl_seconds);
- maximum entry count (max_entries);
- observable hit/miss/expired disposition.

A cache hit is a retrieval optimization. It is not evidence that the cached
content is true, current, independent, or authoritative.

A stale cached item must not be promoted to VERIFIED merely because it was
previously retrieved successfully.

## Retry and backoff

Retry behavior is explicitly bounded by:

- max_attempts;
- initial delay;
- maximum delay;
- backoff multiplier.

The policy must terminate after the configured attempt budget.

Retries are transport behavior. A successful retry means that retrieval
succeeded; it does not mean that the returned claim is true.

## Error handling

Transport failures must remain distinguishable from:

- no relevant evidence;
- unverified evidence;
- conflicting evidence;
- refuted evidence.

A timeout, HTTP failure, parse failure, or exhausted retry budget must not be
silently converted into a factual conclusion.

## Freshness boundary

Transport caching and evidence freshness are related but separate:

retrieval -> retrieved_at -> freshness assessment

The cache TTL is not a universal factual freshness rule. Domain-specific
freshness policies remain explicit and belong to the evidence layer.

## Independence boundary

Retrying the same endpoint does not create an independent source.

Likewise, retrieving the same publisher through different search engines does
not by itself establish independent publisher families.

Source independence remains governed by the source-independence contract.

## Authority boundary

Neither cache state, retry success, backoff state, HTTP success, nor transport
confidence grants action authority.

The existing verification and agency boundaries remain unchanged.

## Intended future integration

A future transport adapter may implement:

1. cache lookup;
2. cache disposition;
3. bounded retrieval attempts;
4. bounded backoff;
5. retrieval result/error classification;
6. retrieved_at propagation;
7. evidence-layer freshness assessment;
8. source-independence and factual verification.

The transport layer must remain provider-independent and domain-agnostic.
