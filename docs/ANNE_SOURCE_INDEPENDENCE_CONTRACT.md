# ANNE Source Independence Contract

## Purpose

ANNE must not treat URL diversity as evidence independence. Twenty pages can
repeat one wire report, press release, or syndicated article.

This contract provides a bounded structural signal: **publisher-family
diversity**. It does not prove that the underlying evidence is independent,
true, current, or authoritative.

## Contract

`provenance -> publisher-family identity -> diversity assessment`

The assessment has three states:

- `multiple_publisher_families`: at least two known publisher families are present.
- `single_publisher_family`: all known sources resolve to one publisher family.
- `unknown`: at least one source identity cannot be established.

Unknown relationships remain unknown.

## Independence boundary

Different domains, URLs, subdomains, or paths do not by themselves prove
independent reporting. A future implementation may add explicit syndication,
canonical-source, or ownership relationships. Until such metadata exists,
ANNE must not infer those relationships from URL uniqueness.

Publisher-family diversity can be used by a verifier or research planner as a
bounded corroboration signal. It must never directly upgrade:

- `UNVERIFIED` to `VERIFIED`
- `CONFLICTING` to `VERIFIED`
- evidence into authority
- freshness into truth

## Relationship to verification

Verification remains responsible for factual status. Source independence is a
precondition/signal that can constrain verification, not a verification result.

For example, two known publisher families can satisfy a structural
multi-family requirement, but the passages can still be contradictory,
duplicated, malformed, injected, or semantically insufficient.

## Non-goals

This contract does not attempt to determine:

- whether two publishers share the same underlying report;
- whether a publisher is trustworthy;
- whether a source is true or false;
- whether a source is current;
- whether a source is authorized to cause an action.

Those are separate contracts.
