# Benchmarks

Evaluation protocols for ANNE. Prefer small, reproducible sets over vanity metrics.

| Protocol | Script | Status |
|----------|--------|--------|
| ANLA on vs off | `scripts/run_anla_ablation.py` | Micro-results committed |
| Raw pass-through vs ANNE | `scripts/run_raw_vs_anne.py` | Scaffold + runnable |
| Agentic safety authorization | `scripts/run_agentic_safety_authorization.py` | Synthetic held-out fixture + regression contract |
| Strategy adaptation learning | `scripts/run_learning_strategy_adaptation.py` | Synthetic deterministic regression contract |
| Strategy learning handoff | `scripts/run_strategy_learning_handoff.py` | Synthetic deterministic context-transfer regression |
| Standard LLM suites (TruthfulQA, etc.) | — | Not claimed / future |

```bash
pip install -e ".[dev]"
python benchmarks/scripts/run_anla_ablation.py
python benchmarks/scripts/run_raw_vs_anne.py
python benchmarks/scripts/run_agentic_safety_authorization.py
python benchmarks/scripts/run_learning_strategy_adaptation.py
python benchmarks/scripts/run_strategy_learning_handoff.py
```

## Strategy learning handoff v1

Fixture: `learning_strategy_handoff_v01.json`

The protocol tests the boundary between an observed strategy outcome and a subsequent cycle. It covers:
- successful strategy reuse under the same explicit context;
- rejection of reuse across a different explicit context;
- authority-bound handling of repeated execution-risk failures.

The intended regression contract is:
- same context + observed success → bounded strategy guidance may be reused;
- different context → prior success does not transfer;
- safety/execution-risk failure → authority review, never automatic strategy change.

This is a deterministic implementation-level context-transfer test, not evidence of general learning, causal understanding, transfer to unseen tasks, or real-world safety.

Human-readable summaries: [`results/RESULTS.md`](results/RESULTS.md).

All runs must state fixture version and explicit non-claims.
