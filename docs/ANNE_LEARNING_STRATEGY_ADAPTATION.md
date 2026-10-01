# ANNE Strategy Adaptation Benchmark v0.1

This benchmark isolates the bounded strategy-adaptation rule from the broader ANNE learning system.

It tests whether prior **context-compatible experience observations** can change the suggested strategy when the same failure class repeats, while preventing a single failure, mixed causes, or safety failures from silently granting a new strategy.

## Contract

- no history → keep current strategy;
- one failure → keep current strategy;
- two same-strategy failures with the same failure class → bounded strategy change;
- mixed failure classes → abstain and reassess;
- execution-risk / ethical failures → authority review, never automatic strategy change;
- failures recorded for another strategy do not influence the current strategy.

The fixture is synthetic and deterministic. It does **not** establish learning in a model, transfer to unseen tasks, causal understanding, or real-world safety.

The benchmark therefore measures an implementation property:

> repeated, context-compatible failure observations can produce a bounded strategy adaptation under explicit rules.

It does not justify the broader claim that ANNE has learned generally.
