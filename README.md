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
See [HARDENING_REPORT_TR.md](HARDENING_REPORT_TR.md) for the Turkish delivery report,
verification instructions, changes, and remaining limitations.

- New memory writes redact recognized credentials at the SQLite/JSON boundaries.
- Empty tool allowlists deny all tools; registered read-tool execution consults AgencyGate.
- Local imports no longer require the Gemini SDK. Install `.[gemini]`, `.[anthropic]`,
  or `.[cloud]` only when those SDKs are needed; base installation remains local-first.
- `AnneAgent` exposes independent factual verification separately from heuristic filtering.
  `require_verified_response=True` withholds responses lacking trusted verification.
- MITOS random fixture scores explicitly retain `SIMULATION` provenance.
- Retry frames recheck FailFast and retain evidence/authority requirements and lineage.
- A frozen-response paired replay records false acceptance/rejection and gate latency.

The default conversational mode can still return factually incorrect, explicitly
unverified text. ANLA is a heuristic filter, not a general fact checker. An optional
`ReferenceVerifier` only matches exact, application-supplied trusted reference claims;
it does not discover facts or validate the authority of arbitrary source strings.

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

---

## Cognitive stages

| Stage | Turkish | Role |
| --- | --- | --- |
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
│   ├── mythos/             Proposal/generative research layer
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

---

## Safety posture

External actions are constrained by allowlists and agency controls. Empty tool allowlists deny tool use. Registered tools consult AgencyGate. Memory writes redact recognized credential patterns at persistence boundaries.

This does **not** mean ANNE is “fully safe” or that safety is solved.

---

## Mathematics, physics and symbolic reasoning

ANNE's research direction includes deterministic symbolic reasoning, derivation tracing, dimensional/unit validation, and physics-oriented computation. These components are treated as **verification and reasoning infrastructure**, not as evidence of general intelligence.

Related themes:

- symbolic manipulation,
- derivation traces,
- unit/dimensional checks,
- reproducible evaluation of symbolic/physical reasoning tasks.

---

## Status summary

| Area | Status |
| --- | --- |
| Six-stage cognitive pipeline | Implemented |
| Persistent/fractal memory + SFT | Implemented |
| Semantic validation / contradiction controls | Implemented in research architecture |
| Agency / tool safety controls | Implemented |
| Neuro-symbolic components | Implemented / experimental |
| Multi-agent collaboration | Experimental |
| Energy-efficiency claims | Hypothesis — requires controlled measurement |
| AGI / consciousness claims | Out of scope — not claimed |

---

## Research program

ANNE is intended to support open, reproducible experimentation around cognitive orchestration. Contributions and collaboration are welcome when they preserve the distinction between implemented mechanisms, experimental features, and hypotheses.

---

## Citation

```
@software{yilmaz2026anne,
  author       = {Yılmaz, Mustafa Gökhan},
  title        = {ANNE – Adaptive Neural Nexus Engine},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/mgy421977-bit/anne-ai},
  orcid        = {0009-0002-6591-0163}
}
```

---

## License

Apache License 2.0 — see LICENSE .

**Author:** Mustafa Gökhan Yılmaz · ORCID 0009-0002-6591-0163 · İzmir, Türkiye
