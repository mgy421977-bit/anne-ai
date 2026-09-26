# ANNE cognitive architecture (overview)

ANNE (Adaptive Neural Nexus Engine) is a **model-agnostic executive / cognitive orchestration** research platform.

## Design stance

- Language models may **propose**; they are not the sole authority.
- Internal organization emphasizes stages, memory, evidence status, ethics, and agency—not “one prompt = one truth”.
- **CURRENT** implementation on `main` includes a multi-stage pipeline, MITOS candidate generation and selection, EvidenceGate, agency modules, fractal memory, and failure traces.
- **TARGET** V1.0 makes evidence → independent verification → agency a single explicit path on factual work.

## Major subsystems (names as in repo)

| Subsystem | Role |
|-----------|------|
| Pipeline / DecisionLoop / CognitiveOrchestrator | Stage execution and entry facades |
| MITOS / mythos | Hypothesis and candidate proposals |
| ANLA + EvidenceGate | Semantic heuristics and evidence-required decision blocking |
| Verification contracts | Factual status types (verified / unverified / …) |
| AgencyGate (core + safety) | Action authorization boundaries |
| FractalMemory | Hypotheses, decisions, rules, SFT, scale events |
| Providers | Optional local / API model backends |
| WebResearcher (`learning/web_research.py`) | Public web retrieval helper on `main` (not a full research product stack) |

## Not in scope of this page

Price intelligence, language-learning curricula, and VITA adapters may exist on **feature branches** and are **not** documented here as `main` production features.
