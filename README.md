# ANNE — Adaptive Neural Nexus Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](https://github.com/mgy421977-bit/anne-ai)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0002--6591--0163-brightgreen)](https://orcid.org/0009-0002-6591-0163)

> **Intelligence is not only prediction. Intelligence is the recursive organization of relationships.**

**ANNE (Adaptive Neural Nexus Engine)** is a research platform for exploring cognitive orchestration around language models. The project separates perception, semantic/contextual processing, memory, verification, safety constraints, tool execution, and model generation rather than treating a foundation model as the sole authority.

ANNE is a **research system, not an AGI claim**. Research boundaries, safety posture, and non-AGI limits are summarized in [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md). The repository deliberately distinguishes implemented engineering from experiments, hypotheses, and future research.

### Local hardening snapshot — September 8, 2026

This archive includes a locally tested hardening patch, not a new upstream release.
See [HARDENING_REPORT_TR.md](HARDENING_REPORT_TR.md) for the Turkish delivery report, verification instructions, changes, and remaining limitations.

- New memory writes redact recognized credentials at the SQLite/JSON boundaries.
- Empty tool allowlists deny all tools; registered read-tool execution consults AgencyGate.
- Local imports no longer require the Gemini SDK. Install `.[gemini]`, `.[anthropic]`, or `.[cloud]` only when those SDKs are needed; base installation remains local-first.
- `AnneAgent` exposes independent factual verification separately from heuristic filtering. `require_verified_response=True` withholds responses lacking trusted verification.
- MITOS random fixture scores explicitly retain `SIMULATION` provenance.
- Retry frames recheck FailFast and retain evidence/authority requirements and lineage.
- A frozen-response paired replay records false acceptance/rejection and gate latency.

The default conversational mode can still return factually incorrect, explicitly unverified text. ANLA is a heuristic filter, not a general fact checker. An optional `ReferenceVerifier` only matches exact, application-supplied trusted reference claims; it does not discover facts or validate the authority of arbitrary source strings.

---

## Chrome Learning Console

The `feature/laptop-web-tinker` branch adds a browser-facing ANNE communication surface. Chrome is the **human interface**, not a second AI brain. Messages are sent to the existing cognitive runtime (`CognitiveConversation`), and the response can expose learning, confidence, verification, and tools used.

The web console intentionally does **not** fall back to Ollama. Select an existing hosted provider explicitly with:

```text
ANNE_WEB_PROVIDER=openai
```

or:

```text
ANNE_WEB_PROVIDER=xai
```

The corresponding provider credentials remain environment variables and are never committed to the repository. If no provider is configured, the console returns a configuration error rather than silently starting a slow local model.

V1 demo identity (password-free, non-auth):

- `Dönerci Mıstık` → Mustafa Bey
- `Gügü Baba` → Gürhan Bey

Memory and experiences are isolated per user_id.

Conceptually:

```text
Human ↔ Chrome Learning Console ↔ ANNE Cognitive Runtime ↔ Model Provider (LanguageInterface only)
                                      │
                                      ├─ memory (user-scoped)
                                      ├─ EpistemicPolicy / ComparisonEngine
                                      ├─ safety / agency gates
                                      └─ bounded tools
```

---

## Official Research Network

**ANNE — AGI-Oriented Open Cognitive Architecture** is the research positioning of this project. ANNE is a research system exploring cognitive orchestration; it does **not** claim achieved AGI, human-level understanding, or support for unsupervised high-stakes autonomous use. See [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).

This repository is the primary implementation surface for ANNE within the Vitavolt Research layer.

| Layer | Resource |
|-------|----------|
| Vitavolt Research (hub) | https://vitavoltglobal.com/research/ |
| ANNE canonical page | https://vitavoltglobal.com/anne.html |
| ANNE research overview | https://vitavoltglobal.com/research/anne-ai.html |
| ANNE architecture | https://vitavoltglobal.com/research/anne-architecture.html |
| Research publication map | https://vitavoltglobal.com/research/publications.html |
| Related core research repo | https://github.com/mgy421977-bit/anne-core |
| Public research profile | https://www.linkedin.com/in/mustafa-g%C3%B6khan-yilmaz-184b4468/ |

**Related repository:** [anne-core](https://github.com/mgy421977-bit/anne-core) is the associated core research prototype (executable, local-first knowledge layer). It belongs to the same research ecosystem and is not a separate product claim.

---

## What ANNE is trying to test

The central research question is:

> Can an additional cognitive orchestration layer improve the reliability, traceability, and controllability of model-assisted reasoning?

No component should be interpreted as proof of consciousness, general intelligence, or safe autonomous operation.

---

## Quick start

Requirements: Python 3.12+.

```bash
git clone https://github.com/mgy421977-bit/anne-ai.git
cd anne-ai
python -m pip install -e ".[dev]"
pytest -q
```

Windows V1: copy `anne_config.env.example` → `anne_config.env`, set provider keys and optional `ANNE_MEMORY_ROOT`, then run `START_ANNE.bat`.

---

## Model providers

```text
Model = LanguageInterface (expression only)
ANNE = orchestration + memory + verification + policy
```
