# ANNE — Technical Due Diligence Readiness

**Status date:** 2026-09-30  
**Scope:** repository-level technical diligence for investor discussion

## 1. Executive technical position

ANNE is currently a research-stage cognitive orchestration platform, not a finished autonomous product.

The implemented architecture separates:

- reasoning from evidence handling;
- evidence from factual verification;
- observation from truth;
- conclusion from authority;
- review from research;
- research from execution;
- learning from automatic permission;
- language corroboration from factual verification.

The current engineering work is best evaluated as a bounded reliability / controllability architecture with persistent, context-scoped learning rather than as a claim of AGI or solved hallucination.

## 2. Implemented architecture

The repository currently contains bounded paths for:

1. canonical DecisionLoop execution;
2. evidence/provenance tracking;
3. multi-source factual verification;
4. research planning and hypothesis/critic/synthesis flow;
5. metacognitive process assessment;
6. bounded metacognitive control;
7. runtime feedback from completed cycles;
8. exact explicit-context experience handoff;
9. persistent episodic experience observations;
10. strategy adaptation and recovery;
11. evidence invalidation and re-evaluation lineage;
12. Turkish language evidence through injected provider boundaries;
13. Bitigçi + TDK language corroboration;
14. language-source divergence as a bounded review signal;
15. preservation of language observations through re-evaluation.

## 3. Safety and authority boundary

Language corroboration is explicitly non-authoritative.

'CORROBORATED' means that independently identified language providers returned matching lexical observations. It does not upgrade factual verification.

'DIVERGENT' means the language observations differ. ANNE routes this to bounded process review; it does not convert divergence into factual refutation and does not automatically authorize new research.

Historical experience is reused only when the current runtime supplies an exact explicit context fingerprint. Empty context receives no historical experience.

Persisted experience remains 'safe_to_reuse=False' unless a separate bounded strategy path permits observation-based reuse. Memory records are observations, not evidence or authority.

## 4. Re-evaluation integrity

Re-evaluation traces preserve:

- parent cycle;
- lineage;
- explicit context;
- language corroboration observation;
- bounded learning outcome.

Re-evaluation cycle identifiers are collision-resistant so repeated invalidation of the same evidence/target pair cannot silently overwrite a prior learning observation.

## 5. Current empirical evidence

The repository contains development-only ablation/replay artifacts.

The 2026-09-08 synthetic paired replay reports:

- RAW: 6/6 accepted, 4 false accepts;
- ANNE: 4 accepted, 2 false accepts, 0 false rejects, 1 evidence-related abstention;
- conditional false-accept rate: 2/4 = 0.5.

The 2026-08-13 ANLA fixture reports:

- ANLA OFF: 30 passed, 15 false passes;
- ANLA ON: 15 passed, 15 blocked, 0 false passes.

These are deliberately documented as development micro-fixtures/synthetic replay. They are **not** independent held-out evaluation and are not evidence of general LLM reasoning improvement.

## 6. Reproducibility infrastructure

The repository contains a GitHub Actions CI workflow covering:

- pytest;
- source/test compilation;
- patch whitespace integrity;
- Ruff;
- mypy.

A CI workflow definition exists, but this branch must not claim a green run unless GitHub exposes the corresponding workflow result.

The benchmark artifacts record source/dataset hashes and generation settings where applicable.

## 7. Remaining investor-grade validation

The principal remaining gap is empirical, not architectural feature count.

Before making quantitative product claims, the following should be demonstrated:

### A. Independent held-out evaluation
Use a fixed, versioned evaluation set that is not tuned to ANNE's rules.

### B. Base-model vs base+ANNE protocol
Compare the same model/task distribution with and without ANNE orchestration.

### C. Multi-seed reporting
Report false-accept, false-reject, abstention, latency and confidence intervals across multiple seeds/runs.

### D. Failure → recovery demonstration
Show a reproducible case where:

'initial result → failure/invalidation → research/review → fresh evidence → re-evaluation → bounded next step'

is visible in the trace.

### E. External technical review
Have an independent reviewer inspect the evidence/authority boundary, persistence semantics and benchmark protocol.

### F. Product validation
Technical architecture alone does not establish product-market fit, customer willingness to pay, or commercial performance.

## 8. Investor communication rule

The technically defensible description is:

> ANNE is a bounded cognitive orchestration and learning architecture designed to make model-assisted reasoning more observable, evidence-aware, reviewable and controllable.

Avoid claims such as:

- hallucination solved;
- AGI;
- human-level understanding;
- autonomous high-stakes authority;
- proven general improvement of all language models.

Those claims require evidence that is not currently established by the repository's development fixtures.

## 9. Recommended diligence package

1. Architecture overview
2. Live failure → recovery trace
3. Evaluation protocol
4. Base model vs ANNE comparison
5. Benchmark result artifacts
6. Reproducibility/CI evidence
7. Security and authority-boundary review
8. Product/pilot evidence
9. Technical roadmap with explicit proof gates

This document is intentionally conservative: the goal is to make the technical boundary inspectable rather than to turn development results into marketing claims.
