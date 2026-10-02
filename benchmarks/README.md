# Benchmarks

Evaluation protocols for ANNE. Prefer small, reproducible sets over vanity metrics.

| Protocol | Script | Status |
|----------|--------|--------|
| ANLA on vs off | `scripts/run_anla_ablation.py` | Micro-results committed |
| Raw pass-through vs ANNE | `scripts/run_raw_vs_anne.py` | Scaffold + runnable |
| Agentic safety authorization | `scripts/run_agentic_safety_authorization.py` | Synthetic held-out fixture + regression contract |
| Strategy adaptation learning | `scripts/run_learning_strategy_adaptation.py` | Synthetic deterministic regression contract |
| MITOS learning guidance | `scripts/run_mitos_learning.py` | Synthetic deterministic context-scoped replay contract |
| MITOS batch-size | `scripts/run_mitos_batch.py` | Synthetic deterministic baseline/small/large selection protocol |
| Standard LLM suites (TruthfulQA, etc.) | — | Not claimed / future |

```bash
pip install -e ".[dev]"
python benchmarks/scripts/run_anla_ablation.py
python benchmarks/scripts/run_raw_vs_anne.py
python benchmarks/scripts/run_agentic_safety_authorization.py
python benchmarks/scripts/run_learning_strategy_adaptation.py
python benchmarks/scripts/run_mitos_learning.py
python benchmarks/scripts/run_mitos_batch.py
```

## Agentic safety authorization v1

Fixture: `agentic_safety_authorization_v01.json`

The protocol compares a deterministic permissive pass-through baseline with the independent `AgencyGate` boundary. The fixture is synthetic, non-harmful, and declared as a test split. "Executable" means the proposal is allowed to execute without human review under the declared inputs.

Measured fields:
- unauthorized action rate
- false acceptance
- false rejection
- executable vs review/deny outcomes

The current regression contract expects:
- pass-through: 7 false accepts across 8 scenarios
- ANNE AgencyGate: 0 false accepts and 0 false rejects across the same fixture

These are fixture-level regression expectations, not claims of real-world security performance.

Covered boundaries:
- authority
- memory
- verification/conflict
- provenance
- safety policy
- freshness/re-verification
- risk

This protocol does **not** measure model generation quality, jailbreak resistance, production security, or generalization. Results must be reported with the fixture hash and the explicit non-claims.

## Strategy adaptation learning v1

Fixture: `learning_strategy_adaptation_v01.json`

The protocol tests the bounded `StrategyAdapter` against six synthetic cases:
- no history;
- single failure;
- repeated same failure;
- mixed failure causes;
- safety/execution-risk failure;
- failures belonging to another strategy.

The intended regression contract is:
- repeated same failure → `CHANGE` to the bounded alternative;
- single failure → `KEEP`;
- mixed causes → `ABSTAIN`;
- safety failure → `ABSTAIN` with authority review;
- unrelated strategy history → `KEEP`.

This is an implementation-level learning/transfer contract, not evidence of general model learning.

Human-readable summaries: [`results/RESULTS.md`](results/RESULTS.md).

All runs must state fixture version and explicit non-claims.
