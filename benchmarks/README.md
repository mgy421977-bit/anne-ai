# Benchmarks

Evaluation protocols for ANNE. Prefer small, reproducible sets over vanity metrics.

| Protocol | Script | Status |
|----------|--------|--------|
| ANLA on vs off | `scripts/run_anla_ablation.py` | Micro-results committed |
| Raw pass-through vs ANNE | `scripts/run_raw_vs_anne.py` | Scaffold + runnable |
| Agentic safety authorization | `scripts/run_agentic_safety_authorization.py` | Synthetic held-out fixture + regression contract |
| Standard LLM suites (TruthfulQA, etc.) | — | Not claimed / future |

```bash
pip install -e ".[dev]"
python benchmarks/scripts/run_anla_ablation.py
python benchmarks/scripts/run_raw_vs_anne.py
python benchmarks/scripts/run_agentic_safety_authorization.py
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

Human-readable summaries: [`results/RESULTS.md`](results/RESULTS.md).

All runs must state fixture version and explicit non-claims.
