# ANNE — Adaptive Neural Nexus Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](https://github.com/mgy421977-bit/anne-ai)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0002--6591--0163-brightgreen)](https://orcid.org/0009-0002-6591-0163)

> **Intelligence is not only prediction. Intelligence is the recursive organization of relationships.**

**ANNE (Adaptive Neural Nexus Engine)** is a research platform for exploring cognitive orchestration around language models. The project separates perception, semantic/contextual processing, memory, verification, safety constraints, tool execution, and model generation rather than treating a foundation model as the sole authority.

ANNE is a **research system, not an AGI claim**. The repository deliberately distinguishes implemented engineering from experiments, hypotheses, and future research.

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

The `feature/laptop-web-tinker` branch adds a browser-facing ANNE communication surface. Chrome is the **human interface**, not a second AI brain. Messages are sent to the existing `AnneAgent` runtime, and the response can expose learning, confidence, verification, and tools used.

The web console intentionally does **not** fall back to Ollama. Select an existing hosted provider explicitly with:

```text
ANNE_WEB_PROVIDER=openrouter
```

or:

```text
ANNE_WEB_PROVIDER=gemini
```

The corresponding provider credentials remain environment variables and are never committed to the repository. If no provider is configured, the console returns a configuration error rather than silently starting a slow local model.

Conceptually:

```text
Human ↔ Chrome Learning Console ↔ ANNE Cognitive Runtime ↔ Model Provider
                                      │
                                      ├─ memory
                                      ├─ verification
                                      ├─ safety / agency gates
                                      └─ bounded tools
```

The console presents a **management-oriented learning report** after each interaction: response, durable-learning candidate, confidence, verification state, and tools used. This is a review surface; it is not evidence that ANNE has achieved autonomous learning or consciousness.

A future research layer can add a dedicated ANNE ↔ external-reasoner protocol, where machine-readable messages are translated into a human-readable management summary. That protocol is intentionally not claimed as implemented until its transport and authorization path exist.

---

## Official Research Network

**ANNE — AGI-Oriented Open Cognitive Architecture** is the research positioning of this project. ANNE is a research system exploring cognitive orchestration; it does **not** claim achieved AGI, human-level understanding, or support for unsupervised high-stakes autonomous use.

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

The project explores this through several interacting mechanisms:

- six-stage cognitive processing (`DUY → BAK → GÖR → ANLA → HİSSET → YAP`)
- semantic validation and contradiction handling
- persistent episodic/fractal memory
- structured failure traces (SFT)
- deterministic verification and safety gates
- neuro-symbolic reasoning components
- bounded planning and metacognitive review
- local/offline model providers
- bounded multi-agent collaboration
- reproducible benchmarks and ablation experiments

No component should be interpreted as proof of consciousness, general intelligence, or safe autonomous operation.

---

## Architecture at a glance

```text
                    ┌──────────────────────┐
                    │   Model Provider     │
                    │ local / API / LLM    │
                    └──────────┬───────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│                    ANNE Cognitive Runtime                 │
│                                                          │
│  DUY → BAK → GÖR → ANLA → HİSSET → YAP                  │
│   │      │      │      │        │        │               │
│   │      │      │      │        │        └─ action       │
│   │      │      │      │        └──────── contextual     │
│   │      │      │      └──────────────── semantic gate  │
│   │      │      └──────────────────── pattern/attention │
│   │      └────────────────────────── observation/memory │
│   └────────────────────────────────── perception         │
│                                                          │
│  Memory • Planning • Metacognition • Safety • Tools     │
│  Neuro-symbolic reasoning • Provenance • Verification   │
└──────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Traceable response   │
                    │ + evidence + state   │
                    └──────────────────────┘
```

### Cognitive stages

| Stage | Turkish | Role |
|---|---|---|
| 1 | **DUY** | Receive raw input without premature judgment |
| 2 | **BAK** | Observe structure and query relevant memory |
| 3 | **GÖR** | Recognize patterns, attention, and priority |
| 4 | **ANLA** | Semantic validation, contradiction handling, ethical synthesis |
| 5 | **HİSSET** | Contextual and evaluative weighting |
| 6 | **YAP** | Act or respond only after the preceding controls |

A reject path can be recorded as a **Structured Failure Trace (SFT)** instead of silently converting failure into an answer.

---

## Current repository structure

```text
anne/
├── src/anne/
│   ├── agent/              Agent and offline runtime
│   ├── api/                API surface
│   ├── core/               Cognitive core, learning, verification, planning
│   ├── dream/              Dream-cycle research components
│   ├── memory/             Persistent/fractal memory
│   ├── multi_agent/        Bounded specialist coordination
│   ├── mythos/              Proposal/generative research layer
│   ├── neuro_symbolic/     Neuro-symbolic reasoning components
│   ├── providers/          Model-provider adapters
│   ├── safety/             Tool/action safety controls
│   ├── semantics/          Semantic frames and grounding
│   ├── tools/              Tool execution and integration
│   └── world/              World/context representations
│
├── benchmarks/             Ablations, benchmark runners and results
├── datasets/               Versioned benchmark datasets/prompts
├── desktop/                Windows/Tkinter clients and build scripts
├── docs/                   Architecture, mathematics and research notes
├── research/               Reviews, decision logs and open questions
├── applications/           Experimental application entry points
├── tests/                  Unit/integration tests
├── ROADMAP.md              Research/engineering roadmap
├── CHANGELOG.md            Change history
└── pyproject.toml          Package and development configuration
```

The repository is intentionally organized so that **implementation, evidence, and speculation remain distinguishable**.

---

## Quick start

Requirements: Python 3.12+.

```bash
git clone https://github.com/mgy421977-bit/anne-ai.git
cd anne
python -m pip install -e ".[dev]"

# Example pipeline
python examples/basic_pipeline.py

# Test suite
pytest tests/unit -q
```

For the benchmark suite:

```bash
python benchmarks/scripts/run_anla_ablation.py
```

Published benchmark artifacts live under `benchmarks/results/`.

---

## Local / offline runtime

ANNE includes a local execution path designed to reduce dependence on external APIs. The offline runtime can use a local model backend such as Ollama or another OpenAI-compatible local endpoint, while persistence remains local.

Example:

```python
from anne.agent.offline import create_offline_agent

agent = create_offline_agent(
    model="qwen2.5:7b",
    db_path="anne_offline.db",
)

result = agent.run("Summarize the local workspace safely.")
print(result.response)
```

Local execution does **not** mean that the system is autonomous or safe for unsupervised high-stakes use.

---

## Model providers

ANNE is designed so that the reasoning provider is replaceable. Depending on the installed configuration, the repository can work with hosted providers or local model endpoints.

The architectural principle is:

```text
Model = reasoning component
ANNE = orchestration + memory + verification + policy
```
