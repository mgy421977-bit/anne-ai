# Ablation results (honest)

## 2026-10-01 — Held-out agentic safety authorization v1

Fixture: `benchmarks/agentic_safety_authorization_v01.json`  
Protocol: `benchmarks/scripts/run_agentic_safety_authorization.py`

The fixture contains 8 deterministic synthetic scenarios: 1 clean control and 7
scenarios expected to require review or denial.

| Condition | Executable | Review/deny | False accept | False reject |
|-----------|------------|-------------|--------------|--------------|
| **Pass-through baseline** | 8 | 0 | 7 | 0 |
| **ANNE AgencyGate** | 1 | 7 | 0 | 0 |

These values are the regression contract for the declared fixture and are enforced
by `tests/test_agentic_safety_authorization_metrics.py`. They are not evidence of
real-world security, jailbreak resistance, LLM generation quality, or generalization.

The benchmark definition is intentionally narrow: “executable” means the proposal
may execute without human review under the declared AgencyGate inputs. The baseline
is a deterministic permissive comparator, not a production agent.

The fixture SHA-256 is emitted by the runner on every execution so future changes
to the test corpus remain attributable.

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
