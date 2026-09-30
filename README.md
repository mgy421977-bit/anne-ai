# ANNE — Adaptive Neural Nexus Engine

> ## 🧠 CANONICAL RESEARCH PLATFORM
>
> **`anne-ai` is the primary research platform for the next-generation ANNE architecture.**
>
> ```text
> anne       → FROZEN LEGACY
> anne-ai    → CANONICAL RESEARCH PLATFORM
> anne-core  → INSTALLABLE CORE LIBRARY
> ```
>
> Active architectural development, integration work, experiments, and research milestones belong here. Reusable, installable core capabilities may be extracted into [`anne-core`](https://github.com/mgy421977-bit/anne-core).
>
> **Canonical project map:**
> - Platform: [`mgy421977-bit/anne-ai`](https://github.com/mgy421977-bit/anne-ai)
> - Installable core: [`mgy421977-bit/anne-core`](https://github.com/mgy421977-bit/anne-core)
> - Legacy/frozen line: [`mgy421977-bit/anne`](https://github.com/mgy421977-bit/anne)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](https://github.com/mgy421977-bit/anne-ai)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0002--6591--0163-brightgreen)](https://orcid.org/0009-0002-6591-0163)

> **Intelligence is not only prediction. Intelligence is the recursive organization of relationships.**

**ANNE (Adaptive Neural Nexus Engine)** is a research platform for exploring cognitive orchestration around language models. It separates model generation from perception, semantic/contextual processing, memory, evidence, verification, metacognition, safety constraints, tool execution, and human/agency boundaries rather than treating a foundation model as the sole authority.

ANNE is a **research system, not an AGI claim**. The repository deliberately distinguishes implemented engineering, bounded experiments, hypotheses, and future research.

---

## What ANNE is trying to test

The central research question is:

> **Can an additional cognitive orchestration layer improve the reliability, traceability, recoverability, and controllability of model-assisted reasoning in measurable ways?**

ANNE explores this through a bounded cognitive runtime that can:

- record canonical cognitive-cycle traces;
- separate evidence from conclusions and authority;
- track provenance and verification state;
- generate and critique bounded research hypotheses;
- perform bounded follow-up research when evidence remains unresolved;
- invalidate stale evidence and perform bounded re-evaluation;
- evaluate how a reasoning process was reached through metacognition;
- retain experience observations within an explicit runtime context;
- adapt strategy from observed context-scoped outcomes;
- preserve human/agency boundaries and fail closed on unauthorized action;
- expose language evidence as a non-authoritative process observation;
- compare independent language-source observations without turning corroboration into factual truth.

No component should be interpreted as proof of consciousness, general intelligence, human-level understanding, or safe autonomous operation.

---

## Core architectural principle

ANNE treats the model as a **reasoning component**, not as the final authority.

```text
MODEL
  │
  ▼
COGNITIVE ORCHESTRATION
  │
  ├── Context / Intent
  ├── Semantic Processing
  ├── Memory
  ├── Evidence
  ├── Verification
  ├── Research
  ├── Re-evaluation
  ├── Metacognition
  ├── Experience / Strategy Adaptation
  └── Safety / Agency
          │
          ▼
   Human / Execution Boundary
```

The governing distinction is:

```text
Evidence      ≠ Conclusion
Conclusion    ≠ Authority
Observation   ≠ Truth
Learning      ≠ Automatic Permission
Corroboration ≠ Factual Verification
Review        ≠ Research
Research      ≠ Execution
```

This separation is a core architectural constraint.

---

## Bounded cognitive feedback loop

The current research runtime is designed around an observable, bounded feedback loop:

```text
INPUT
  ↓
REASONING / RESEARCH
  ↓
RESULT
  ↓
CANONICAL CYCLE TRACE
  ↓
METACOGNITIVE ASSESSMENT
  ├── COMPLETE
  └── REVIEW
        ├── RESEARCH
        └── BOUNDED REVIEW
  ↓
EXPERIENCE OBSERVATION
  ↓
EXACT CONTEXT-SCOPED REUSE
  ↓
NEXT CYCLE
```

The metacognitive layer is **observational**. It does not certify truth, infer causality, grant execution authority, or override evidence and agency gates.

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
│   │      │      │      └──────────────── semantic        │
│   │      │      └────────────────────── pattern          │
│   │      └──────────────────────────── observation/memory│
│   └────────────────────────────────── perception          │
│                                                          │
│ Evidence • Verification • Research • Re-evaluation       │
│ Metacognition • Experience • Strategy • Safety • Agency  │
│ Provenance • Language Evidence • Traceability            │
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
| 4 | **ANLA** | Semantic validation, contradiction handling, and synthesis |
| 5 | **HİSSET** | Contextual and evaluative weighting |
| 6 | **YAP** | Respond or act only after preceding controls |

A reject path can be recorded as a **Structured Failure Trace (SFT)** instead of silently converting failure into an answer.

---

## Evidence, verification, and research

ANNE maintains explicit distinctions between evidence state and process state.

### Factual verification

The bounded verification path supports:

```text
VERIFIED
REFUTED
UNVERIFIED
CONFLICTING
```

Evidence required for a decision must carry explicit provenance and pass the applicable verification gate before becoming available as verified evidence.

Memory, model confidence, search results, or accumulated observations do not become authoritative merely because they exist.

### Bounded research

The Research Cognitive Loop provides:

- bounded subquestions;
- source/query budgets;
- stop conditions;
- hypothesis generation;
- alternative hypotheses;
- critique;
- evidence ledger integration;
- provenance-aware synthesis;
- follow-up research for unresolved evidence;
- bounded re-evaluation after evidence invalidation.

### Re-evaluation

When evidence becomes stale or invalid:

```text
STALE / INVALID EVIDENCE
          ↓
FRESH RESEARCH
          ↓
REPLACEMENT EVIDENCE
          ↓
RE-EVALUATION
          ↓
NEW BOUNDED TRACE
```

Historical provenance remains preserved rather than silently rewriting the past.

---

## Metacognition

ANNE's metacognitive layer evaluates the **recorded reasoning process**, not truth itself.

Current process states include:

- `PROCESS_COMPLETE`
- `PROCESS_REVIEW_REQUIRED`

Metacognition can record:

- known process dependencies;
- unknowns;
- evidence basis;
- assumptions;
- decision dependencies;
- recalibration triggers;
- whether further research is required;
- why review or research was requested.

Example:

```text
VERIFIED + provenance
        ↓
PROCESS_COMPLETE

UNVERIFIED
        ↓
PROCESS_REVIEW_REQUIRED
        ↓
bounded research

language-source divergence
        ↓
PROCESS_REVIEW_REQUIRED
        ↓
bounded review
```

A metacognitive observation never grants execution authority.

---

## Context-scoped experience and bounded learning

ANNE does not treat every past experience as globally reusable.

Experience observations carry an explicit context fingerprint and are recalled only when the current runtime context matches the recorded context.

```text
CURRENT EXPLICIT CONTEXT
          ↓
EXACT CONTEXT FINGERPRINT
          ↓
MATCHED EXPERIENCE OBSERVATIONS
          ↓
BOUNDED STRATEGY ADAPTATION
```

Important constraints:

- empty context receives no historical experience;
- semantic guessing is not used to infer missing context;
- cross-context observations are isolated;
- experience is stored as observation, not truth;
- `safe_to_reuse` does not grant execution authority;
- parent cycles and lineage are retained for re-evaluation history;
- learning claims still require reproducible experiments.

A correct answer is not, by itself, evidence that ANNE learned.

---

## Turkish language evidence and corroboration

ANNE includes a bounded language-evidence layer designed around injected, approved provider resolvers.

The current research path includes:

- a provider-neutral language evidence contract;
- a bounded Bitigçi adapter;
- a bounded TDK adapter;
- a language evidence → research ledger bridge;
- explicit high-ambiguity lookup policy;
- language evidence preservation in canonical traces;
- independent-source language corroboration;
- language divergence detection;
- runtime metacognitive observation of language divergence;
- preservation of language corroboration through re-evaluation lineage.

The architecture intentionally separates:

```text
LANGUAGE CORROBORATION
        ≠
FACTUAL VERIFICATION
        ≠
AUTHORITY
```

For example:

```text
Bitigçi + TDK
      ↓
same lexical observation
      ↓
CORROBORATED
      ↓
process observation only

different lexical observations
      ↓
DIVERGENT
      ↓
bounded REVIEW
      ↓
not REFUTED
```

Providers do not use undocumented HTTP calls or scraping through the ANNE core. Approved resolver injection is required.

---

## Human and agency boundary

ANNE is designed so that reasoning and learning do not automatically become action permission.

```text
MODEL OUTPUT
     ↓
EVIDENCE / VERIFICATION
     ↓
METACOGNITION
     ↓
STRATEGY / RESEARCH DECISION
     ↓
AGENCY GATE
     ↓
HUMAN / EXECUTION BOUNDARY
```

Action requests without an explicit authority decision remain `REVIEW`.

Evidence-required decisions remain blocked until the applicable provenance-bearing verification requirement is satisfied.

These are engineering controls, **not a safety certification**.

---

## Current repository structure

```text
anne/
├── src/anne/
│   ├── agent/              Agent and offline runtime
│   ├── api/                API surface
│   ├── core/               Cognitive core, traces, learning, verification
│   ├── dream/              Dream-cycle research components
│   ├── language/           Bounded Turkish language evidence/corroboration
│   ├── learning/           Research, metacognition, experience, strategy
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
cd anne-ai
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

Recommended local checks before merging a change:

```bash
ruff check .
mypy src
pytest -q
```

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

ANNE is designed so that the reasoning provider is replaceable.

```text
Model = reasoning component
ANNE  = orchestration + memory + evidence + verification + policy
```

Depending on configuration, ANNE can use hosted providers or local model endpoints.

The model output is therefore not treated as unconditional authority for tool use or external action.

---

## Reliability and safety layer

The current architecture includes conservative controls such as:

- allowlisted tool policies;
- credential redaction before durable memory writes;
- evidence and provenance tracking;
- contradiction handling;
- deterministic verification paths;
- bounded research budgets;
- bounded retries;
- provenance invalidation and re-evaluation;
- explicit agency metadata;
- fail-closed action routing;
- human-review boundaries;
- context-scoped experience reuse.

These mechanisms are engineering controls, **not a safety certification**.

---

## Benchmarks and evidence

The repository contains:

- ANLA ablation experiments;
- benchmark datasets/prompts;
- reproducible runner scripts;
- committed result artifacts;
- paired replay experiments;
- research reviews and decision records.

Current published development artifacts include small controlled fixtures and synthetic replay experiments. These are **not independent held-out evaluations and are not evidence of general LLM reasoning improvement**.

For example, the repository records an ANLA ON/OFF micro-fixture and a paired replay with explicit false-accept/false-reject accounting. The project intentionally retains limitations and does not convert these development results into broad performance claims.

See:

- [`benchmarks/`](benchmarks/)
- [`benchmarks/results/`](benchmarks/results/)
- [`ROADMAP.md`](ROADMAP.md)
- [`research/`](research/)

**Evidence first:** a capability should be promoted from hypothesis to implemented result only when corresponding code, tests, or benchmark artifacts exist.

---

## Current project status — September 30, 2026

**Research Preview / Alpha — active development**

| Area | Current position |
|---|---|
| Six-stage cognitive pipeline | Implemented |
| Persistent/fractal memory + SFT | Implemented |
| Semantic validation / contradiction controls | Implemented / research |
| Cognitive workspace / planning | Implemented / bounded |
| Evidence Ledger + provenance | Implemented / bounded |
| Multi-source factual verification | Implemented / bounded |
| Bounded research loop | Implemented / bounded |
| Hypothesis generation + critique | Implemented / bounded |
| Decision Synthesis | Implemented / bounded |
| Provenance invalidation + re-evaluation | Implemented / bounded |
| Metacognitive process evaluation | Implemented / bounded |
| Runtime metacognitive feedback | Implemented / bounded |
| Context-scoped experience handoff | Implemented / bounded |
| Context-aware strategy adaptation | Implemented / bounded |
| Re-evaluation lineage | Implemented / bounded |
| Turkish language evidence provider layer | Implemented / bounded |
| Turkish language corroboration | Implemented / bounded |
| Language divergence → bounded review | Implemented / bounded |
| Language corroboration through re-evaluation | Implemented / bounded |
| Local/offline runtime | Implemented |
| Model-provider abstraction | Implemented |
| Safety and agency controls | Implemented / conservative |
| Multi-agent coordinator | Experimental / bounded |
| Benchmark and ablation infrastructure | Implemented |
| Independent held-out evaluation | **Not yet established** |
| General intelligence / AGI | **Not claimed** |
| Human-level understanding | **Not claimed** |
| Unsupervised high-stakes deployment | **Not supported** |

**Important:** “Implemented / bounded” means that the corresponding engineering capability exists in the repository with bounded tests or integration coverage. It does **not** mean universally reliable, scientifically proven, production-certified, or equivalent to general intelligence.

---

## Engineering progress — September 30, 2026

### Evidence and research infrastructure

- ✓ Bounded research runtime
- ✓ Evidence Ledger and provenance-bearing evidence
- ✓ Evidence passages retained in research traces
- ✓ Independent-source handling for bounded verification
- ✓ `VERIFIED`, `REFUTED`, `UNVERIFIED`, and `CONFLICTING` factual states
- ✓ Research Planner with bounded budgets and stop conditions
- ✓ Research Cognitive Loop
- ✓ Hypothesis generation and critique
- ✓ Alternative hypothesis preservation
- ✓ Provenance Graph and downstream invalidation
- ✓ Fresh replacement evidence and bounded re-evaluation
- ✓ Decision Synthesis
- ✓ Canonical runtime cycle traces

### Metacognition and adaptive learning

- ✓ Formal bounded metacognitive assessment
- ✓ Explicit process completion/review semantics
- ✓ Bounded routing of metacognitive review through research control
- ✓ Runtime metacognitive feedback loop
- ✓ Separation of factual status from process status
- ✓ Context-scoped persistent experience observations
- ✓ Exact explicit-context matching
- ✓ Context-aware strategy selection
- ✓ Strategy outcome and recovery observations
- ✓ Parent-cycle and lineage preservation
- ✓ Bounded experience handoff across sequential runtime cycles

### Turkish language evidence

- ✓ Provider-neutral language evidence contract
- ✓ Bounded Bitigçi adapter
- ✓ Bounded TDK adapter
- ✓ Language evidence → research ledger bridge
- ✓ High-ambiguity language lookup policy
- ✓ Language evidence in canonical cycle traces
- ✓ Explicit-provider language corroboration
- ✓ `CORROBORATED` / `DIVERGENT` / `INSUFFICIENT` language states
- ✓ Non-authoritative language corroboration
- ✓ Language divergence routed to bounded review
- ✓ Language corroboration preserved through re-evaluation lineage

### Safety / agency

- ✓ ToolPolicy and AgencyGate remain fail-closed for unauthorized action
- ✓ Evidence-required decisions remain gated by applicable verification requirements
- ✓ Action requests without explicit authority remain `REVIEW`
- ✓ Credential redaction and bounded retry controls remain in the guarded runtime path
- ✓ Language corroboration cannot modify factual verification or execution authority

---

## What remains to be proven

The architecture is ahead of the empirical evidence. The next major work is therefore **measurement, not bigger claims**.

### Priority 1 — Independent evaluation

Build controlled evaluation suites that compare:

```text
BASE MODEL
    vs
BASE MODEL + ANNE
```

using held-out tasks and reproducible protocols.

Measure, where applicable:

- false acceptance;
- false rejection;
- unsupported conclusions;
- provenance coverage;
- contradiction detection;
- research activation;
- recovery success;
- repeated-error rate;
- latency;
- resource/API cost;
- human-review frequency.

### Priority 2 — Reproducibility

- expose a stable benchmark protocol;
- run multiple seeds where applicable;
- publish raw result artifacts;
- record dataset and source hashes;
- separate development fixtures from held-out evaluation;
- keep CI/test evidence visible and reproducible.

### Priority 3 — Product validation

The current project is a research platform rather than a finished commercial product.

Before commercial positioning, the project needs evidence for:

- a concrete user/problem;
- repeatable workflow value;
- measurable improvement;
- operating cost;
- deployment model;
- pilot usage;
- scalability.

---

## Research discipline

ANNE uses four practical labels:

- **IMPLEMENTED** — present in the repository and testable.
- **IMPLEMENTED / BOUNDED** — implemented with explicit limits and controlled evaluation.
- **EXPERIMENTAL** — implemented for research evaluation; not established as generally reliable.
- **HYPOTHESIS / ROADMAP** — a research proposition or planned work that should not be described as a current capability.

This distinction is a core part of the project.

---

## Known limitations

ANNE remains an active research platform.

Current limitations include:

- benchmark evidence is not yet an independent held-out demonstration of general improvement;
- some research components remain experimental or bounded;
- metacognition evaluates recorded process state and does not establish truth;
- experience observations do not constitute proof of learning;
- language corroboration does not constitute factual verification;
- local/offline execution does not imply autonomous safety;
- external model providers remain subject to their own failure modes;
- CI workflow/status evidence may not be available for every stacked research branch;
- no claim is made that ANNE solves hallucinations in general;
- no claim is made that ANNE achieves AGI or human-level understanding.

---

## Roadmap

The roadmap prioritizes evidence before expansion:

1. strengthen benchmark coverage and measurement;
2. validate semantic gates and failure paths;
3. measure learning/transfer independently from calculation correctness;
4. establish base-model vs base+ANNE evaluation;
5. improve reproducibility and multi-seed evaluation;
6. validate product/pilot use cases;
7. expand advanced multi-agent and long-term planning research only after evidence supports it.

See [`ROADMAP.md`](ROADMAP.md) for milestone-level criteria.

---

## Citation

```bibtex
@software{yilmaz2026anne,
  author       = {Yılmaz, Mustafa Gökhan},
  title        = {ANNE – Adaptive Neural Nexus Engine},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/mgy421977-bit/anne-ai},
  orcid        = {0009-0002-6591-0163}
}
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

**Author:** Mustafa Gökhan Yılmaz · ORCID [0009-0002-6591-0163](https://orcid.org/0009-0002-6591-0163) · İzmir, Türkiye


---

## Investor technical diligence

[`docs/INVESTOR_TECHNICAL_DUE_DILIGENCE.md`](docs/INVESTOR_TECHNICAL_DUE_DILIGENCE.md) documents the current architecture, empirical evidence, limitations, reproducibility boundaries, and remaining investor-grade proof requirements.
