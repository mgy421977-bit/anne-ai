# ANNE V1.0 gap analysis (documentation snapshot)

Aligned with independent code audits of `main` vs feature branches. **No feature is marked complete without code+tests on main.**

## Stronger on main

- Multi-stage pipeline, orchestrator path, FailFast, ambiguity
- MITOS candidate generation + selection
- EvidenceGate on evidence-required paths (with tests)
- Agency gate modules + tests
- FractalMemory + failure traces
- Optional model providers; offline-oriented paths

## Gaps vs TARGET V1.0

- Single unified agency runtime path
- Full independent verification pipe on all factual entry points
- ANLA is a gate/heuristic—not a complete verification engine
- General research package / WebSearchProvider stack lives primarily on **feature branches**, not as committed main product surface
- CI workflows not established on main in prior audits
- Price / language-learning / VITA adapter: extension territory

## Feature branches (not main)

Branches such as `feature/research-language-learning`, `feature/anne-canonical-client-entry`, and `feature/evidence-boundary-hardening` may contain additional research, evidence, or runtime experiments. Treat them as **unmerged work** until reviewed, tested, and merged.
