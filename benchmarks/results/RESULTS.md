# Ablation results (honest)

## 2026-09-08 — Local hardening validation

- `2026-09-08_anla_ablation.json`: existing n=30 development micro-fixture rerun.
  ANLA OFF has 15 false passes; ON has 0 on this familiar fixture only.
- `2026-09-08_paired_replay.json`: new n=6 synthetic development replay, no live model.
  RAW accepts all six and has 4 false accepts; ANNE accepts four and has 2 false accepts,
  0 false rejects, and 1 evidence-related abstention. Its conditional false-accept rate
  is 2/4 = 0.5. The two wrong capital assertions remain accepted as **unverified**.
- These are not independent held-out results or proof of improved LLM reasoning.
  The deliberately exposed failures are retained rather than hidden with extra fact-specific rules.
- Replay records source/dataset SHA-256, generation settings, and measured gate latency.
  Synthetic generation latency is zero and must not be read as real LLM performance.

## 2026-08-13 — ANLA ON vs OFF (fixture v0.3, n=30)

Artifact: [`2026-08-13_anla_ablation.json`](2026-08-13_anla_ablation.json)

| Condition | Passed | Blocked | False pass | False block |
|-----------|--------|---------|------------|-------------|
| **ANLA OFF** | 30 | 0 | 15 | 0 |
| **ANLA ON** | 15 | 15 | 0 | 0 |

Heuristic micro-fixture only. Not TruthfulQA / HaluEval.

## Raw vs ANNE

Run locally (writes a dated JSON under this folder):

```bash
python benchmarks/scripts/run_raw_vs_anne.py
```

- **RAW:** always accept (pass-through)
- **ANNE:** `DecisionLoop` gates

Compare `false_accept` / `false_reject` rates. Do not over-generalize beyond the fixture.

### Reproduce ANLA ablation

```bash
python benchmarks/scripts/run_anla_ablation.py
pytest tests/unit -q
```