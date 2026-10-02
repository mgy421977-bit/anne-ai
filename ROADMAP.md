# ANNE Development Roadmap

**Policy:** Milestones are engineering deliverables, not product promises.  
**Rule:** No public claim of “hallucination solved” or “AGI” until the matching benchmark row is green and published under benchmarks/results/.

Last updated: 2026-10-02

---

## North star (research hypothesis)

> Does a cognitive orchestration layer — Semantic Validation Layer (ANLA), ethical decision constraints, Structured Failure Traces (SFT), and experience-driven discovery — improve reliability, discovery quality, and controllability of model-assisted reasoning in a measurable way?

Success is **evidence**, not slogans.

---

## Current baseline — v0.1.0 Research Preview

> **Current engineering note (2026-10-01):** The repository has progressed beyond the original v0.1.0 baseline with bounded evidence/provenance, research planning and cognitive follow-up, hypothesis/critique, Decision Synthesis, provenance-driven re-evaluation, and MITOS runtime handoff coverage. MITOS observations are now covered at the DecisionLoop boundary: same-context repeated bounded failures can drive a strategy change in the direct research loop, while mixed-cause runtime failures trigger a guarded ABSTAIN/reassessment path. The authority boundary remains fail-closed. These are implemented research capabilities; the roadmap remains the authority for future empirical milestones.

| Deliverable | Status |
|-------------|--------|
| Six-stage pipeline (DUY…YAP) | Done |
| EthicCore + axioms | Done |
| FractalMemory + SFT | Done |
| Mythos (placeholder / API) | Done |
| ANLA score skeleton | Done (A3 context-consistency contract implemented; PR #132, commit fd8d147663231c6514b45acd07dd35d148b23c83) |
| Ablation scaffold | Done (A2 CI execution + raw artifact published; PR #134, commit 4f33e22ca5c941bcc29472c713b5608e7394bb12) |
| Independent review response | Done |
| MITOS architecture specification | Experimental proposal |
| MITOS → AdaptiveLearning → DecisionLoop runtime handoff regression coverage | Done (PR #130, commit ced5f718e65962fc69782598b6fbac043055f1e7) |

---

## Phase A — Evidence (v0.2) · target ~4–8 weeks

**Goal:** First numbers that can survive Ben Dixon–style “grade against the source” scrutiny.

| ID | Milestone | Exit criteria |
|----|-----------|---------------|
| A1 | Expand ablation fixture (≥30 prompts, coherent/incoherent/conflict) | **Done** — versioned fixture v0.3 with 30 prompts (15 coherent / 15 incoherent) |
| A2 | Run ANLA ON vs OFF; save raw JSON under benchmarks/results/ | **Done** — CI run #605 green; raw artifact generated from merge commit c8bacd3; 30 cases, 15 blocked with ANLA ON vs 0 blocked with ANLA OFF |
| A3 | Implement heuristic $S_{ANLA}$ (overlap + contradiction + SFT penalty) in pipeline path | **Done** — DUY input ↔ candidate $C_{ctx}$ contract tests + unit/integration coverage; PR #132, commit fd8d147663231c6514b45acd07dd35d148b23c83 |
| A4 | Retry-loop bound (max N returns to DUY) | **Done** — bounded retry tests; PR #133, commit 25961c6e43e54efe5f2c0b6df234011df3dd86e6 |
| A5 | CI: pytest must pass; ruff clean on main | In progress — PR #134 CI is green; post-merge main workflow evidence still needs verification |

**A3 completion note (2026-10-02):** The context-consistency contract identified by the independent audit is now implemented and covered by falsifiable tests. `C_ctx` receives both DUY input and candidate text, while ANLA remains a semantic/consistency gate rather than a factual verifier. See `research/decision_logs/2026-10-02_a3_context_consistency_contract.md` and PR #132.

**Non-goals for v0.2:** TruthfulQA leaderboard claims, VSA, BCI, neuromorphic hardware.

---

## Phase B — Measurement (v0.3) · target ~2–3 months after A

**Goal:** Stronger semantic proxies and transparent metrics.

| ID | Milestone | Exit criteria |
|----|-----------|---------------|
| B1 | Optional embedding / NLI backend for $C_{ctx}$, $C_{log}$ | Pluggable; default remains heuristic |
| B2 | Micro-suite inspired by contradiction & factual error patterns | Documented limitation vs full TruthfulQA |
| B3 | Report false-accept / false-reject / latency | benchmarks/results/ + short note in docs/ |
| B4 | Vector or hybrid retrieval experiment (optional) behind flag | Feature flag; SQLite remains default |
| B5 | Pipeline integration tests (full HEAR→ACT + SFT path) | Coverage of reject and approve paths |

### Phase B-M — MITOS Discovery & Experience Loop (experimental)

**Goal:** Test whether a bounded, high-volume hypothesis generator can improve ANNE's later selection, calibration, discovery value or computation efficiency.

| ID | Milestone | Exit criteria |
|----|-----------|---------------|
| M1 | MITOS exploration API | EXPLORE / COMBINE / INVERT / SIMULATE interfaces with bounded output |
| M2 | Hypothesis/experience schema | HYPOTHESIS → PREDICTION → TESTED → VERIFIED/FAILED/INCONCLUSIVE |
| M3 | ANNE evaluation gate | Probability, benefit, novelty, testability, cost, harm-risk and uncertainty recorded |
| M4 | Low-probability/high-value ranking experiment | Low-probability candidates remain eligible when test cost and harm risk are sufficiently low |
| M5 | Reality feedback loop | Observed outcome stored separately from prediction; prediction error recorded |
| M6 | MITOS learning guidance | **Done** — deterministic context-scoped replay artifact; PR #141, merge `6bde60006b088799a6f118e6a929fe8c7b62dd7c`; 4/4 contract cases pass |
| M7 | Batch-size benchmark | Compare small vs larger MITOS batches against baseline generation |

**Important:** M1–M7 are research milestones, not claims that MITOS currently learns or improves ANNE. Results must be published as benchmark artifacts.

---

## Phase C — Scale & paper readiness (v0.4) · target ~4–6 months after B

**Goal:** Publishable experimental section, still not “AGI product”.

| ID | Milestone | Exit criteria |
|----|-----------|---------------|
| C1 | Multi-seed ablation + confidence intervals | Repro script + fixed seeds |
| C2 | Comparison protocol: base model vs base+ANNE orchestration | Written protocol in benchmarks/ |
| C3 | Preprint / technical report draft | papers/ with honest limitations |
| C4 | Optional multi-agent experiment (Mythos proposals × Core veto) | Logged SFTs across agents |
| C5 | API surface freeze candidate | Versioned anne package API docs |

---

## Phase D — Long horizon (v1.0+) · no calendar promise

Only after A–C evidence exists. Parked by independent review until then:

- Formal ANLA theory (beyond skeleton)
- VSA / symbolic–continuous bridge research notes
- CMS-scale memory (beyond single SQLite file)
- Neuromorphic / edge targets
- BCI / bio-coupling **research only** — never a v0.x claim

These may live under papers/whitepaper/ and research/open_questions/ without implying implementation.

---

## Priority order (if time is scarce)

1. **A2 + A3** — numbers + real gate path  
2. **A4** — safety of retry loops  
3. **M2 + M5 + M6** — make experience and learning measurable  
4. **M4 + M7** — test low-probability/high-value discovery  
5. **B2 + B3** — clearer metrics  
6. **C2 + C3** — external communication  
7. Everything in Phase D

---

## Anti-roadmap (explicitly deferred)

- Marketing “zero hallucination”
- Landauer / thermodynamic explanations of semantics
- GROMACS-driven cognitive weights
- Claiming medical / high-stakes readiness
- Treating simulated outcomes as real-world facts
- Treating accumulated memory records alone as evidence of learning

---

## How to update this file

1. Move a row to Done only with a linked commit or benchmarks/results/ artifact.  
2. Log scope changes under research/decision_logs/.  
3. Keep README status table in sync with this roadmap.  
4. Keep MITOS research claims separate from implemented capabilities until the corresponding experiment is reproducible.
