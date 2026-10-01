# ANNE Strategy Learning Handoff v0.1

This protocol tests whether an observed strategy outcome can influence a subsequent cycle only when the explicit context matches.

## Contract

- an observed successful strategy may be selected for the next cycle only under the same explicit context;
- a successful strategy observed in another context must not transfer;
- safety/execution-risk failures remain authority-bound and do not become automatic strategy changes;
- historical observations remain non-authoritative and are never treated as factual verification.

The fixture is synthetic and deterministic. It measures an implementation property of context-scoped strategy reuse, not general learning, causal understanding, transfer, or real-world safety.

The intended boundary is:

OBSERVE -> CONTEXT MATCH -> BOUNDED STRATEGY GUIDANCE -> NEXT CYCLE

not:

OBSERVE -> AUTOMATIC AUTHORITY
