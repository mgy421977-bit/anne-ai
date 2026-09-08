# Changelog

## Local hardening snapshot — 2026-09-08 (not an upstream release)

- Centralized credential-pattern redaction for new parameterized SQLite memory writes,
  JSON terminology records, and outgoing GitHub memory documents.
- Fixed empty allowlists, optional Gemini imports, the stale GapFiller test import,
  and semantic rejection's state-level HALT status.
- Added explicit factual-verification contracts, provenance checks, strict abstention,
  and a bounded trusted-reference adapter; model confidence is not verification.
- Narrowed one class of lexical false rejections and marked simulated candidate scores.
- Rechecked FailFast on retries, preserved authority/evidence requirements, persisted
  retry ancestry, and made cognitive hypothesis IDs unique across cycles.
- Removed automatic confidence bonuses from repeated learned-rule records.
- Added paired replay, regression tests, validation logs, and a Turkish delivery report.
- CI checks without modifying source files and covers Python 3.12/3.13 test configurations.

## [0.1.0] — 2026-07-29 — Research preview

### Added
- Six-stage cognitive pipeline (DUY/HEAR → … → YAP/ACT)
- EthicCore operational axioms and decision score
- FractalMemory (SQLite) with hypotheses, decisions, patterns, empathy map
- **failure_traces** table + API for ANLA reject path
- Mythos curiosity loop (placeholder + optional Anthropic API)
- Dream cycle offline pattern synthesis
- ANLA semantic score **skeleton** (`docs/mathematics/`)
- ANLA ON vs OFF **ablation scaffold** + micro fixture
- Unit tests for EthicCore and FractalMemory
- Independent review archive + scope-reduction decision log
- Governance docs, system card, CITATION.cff, Apache-2.0

### Explicit non-goals for 0.1.0
- No TruthfulQA / HaluEval published numbers
- No VSA / TRC² / BCI / neuromorphic runtime
- No claim of zero hallucination or “mathematically verified AGI”