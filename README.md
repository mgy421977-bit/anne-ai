# ANNE AI

**Experimental Cognitive Architecture for General-Purpose Intelligence**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](https://github.com/mgy421977-bit/anne-ai)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0002--6591--0163-brightgreen)](https://orcid.org/0009-0002-6591-0163)

> **ANNE is an experimental cognitive architecture and AGI candidate concept exploring a path toward general-purpose intelligence.**
>
> **ANNE is not presented as a completed AGI system.**

### Positioning (read this first)

| Term | Meaning for this repository |
|------|-------------------------------|
| **AGI candidate concept** | A research architecture direction worth testing for general-purpose intelligence |
| **Not AGI** | No claim of completed AGI, human-level intelligence, or solved general reasoning |
| **Current** | What `main` implements and tests today |
| **Target** | V1.0 cognitive-loop design still being integrated |

**ANNE is not an energy-sector AI product.** Energy / engineering scenarios (for example GES–BESS planning) are **application domains** used to exercise the architecture. Domain computation belongs to other systems (see [Vitavolt / VITA boundary](docs/applications/VITAVOLT-VITA.md)).

```text
ANNE AI            → general cognitive / reasoning architecture research
VITA Intelligence  → decision / user-facing intelligence layer
VITA Engine        → engineering computation / domain execution
Vitavolt Global    → real-world engineering and business applications
```

ANNE does **not** depend on VITA. VITA may call ANNE; ANNE remains a standalone research platform.

### Repository map

```text
anne       → FROZEN LEGACY
anne-ai    → CANONICAL RESEARCH PLATFORM  (this repo)
anne-core  → INSTALLABLE CORE LIBRARY
```

- Platform: https://github.com/mgy421977-bit/anne-ai
- Installable core: https://github.com/mgy421977-bit/anne-core
- Legacy: https://github.com/mgy421977-bit/anne

### Research question

> Can general-purpose intelligence be approached through a cognitive architecture built around hypothesis generation, evidence boundaries, verification, memory, metacognition, agency constraints, abstention, and bounded iterative reasoning?

Related research areas: cognitive architectures, AGI architectures, hypothesis generation, evidence-aware reasoning, verification-aware AI, metacognition, AI memory, failure-aware learning, AI abstention, agency boundaries, human–AI decision boundaries.

### Target cognitive loop (V1.0 design)

```text
FAILFAST → DUY → BAK → AMBIGUITY → GÖR → MITOS → SELECT
  → ANLA → EVIDENCE → INDEPENDENT VERIFICATION
  → HİSSET → AGENCY GATE → YAP | ABSTAIN
  → MEMORY → FAILURE TRACE → bounded NEXT CYCLE
```

This diagram is the **target** architecture. Parts of it exist on `main` (pipeline stages, MITOS/select, EvidenceGate, agency modules, memory, failure traces). Full end-to-end evidence→independent verification→agency on every path is **not** claimed as production-complete. See [CURRENT vs TARGET](docs/architecture/COGNITIVE-LOOP.md) and [V1 gap analysis](docs/spec/ANNE-V1-GAP-ANALYSIS.md).

### Non-negotiable boundaries

- **Hypothesis ≠ Fact** (MITOS candidates are proposals; default evidence status is unverified)
- **Memory ≠ Evidence** (a prior decision is not independent verification)
- **Candidate ≠ Verified knowledge**
- **Search hit ≠ Verified**
- **Good answer ≠ Permission to act** (Agency Gate / human approval where required)

Discipline: **Run. Measure. Verify. Then claim.**

### Documentation index

| Doc | Purpose |
|-----|---------|
| [AGI positioning](docs/research/AGI-POSITIONING.md) | AGI candidate research stance |
| [Research questions](docs/research/RESEARCH-QUESTIONS.md) | Open technical questions |
| [Cognitive architecture](docs/architecture/ANNE-COGNITIVE-ARCHITECTURE.md) | Architecture overview |
| [Cognitive loop](docs/architecture/COGNITIVE-LOOP.md) | Stage map CURRENT vs TARGET |
| [Evidence governance](docs/architecture/EVIDENCE-GOVERNANCE.md) | Unverified → verified boundary |
| [Agency boundary](docs/architecture/AGENCY-BOUNDARY.md) | Action authorization |
| [Memory and failure](docs/architecture/MEMORY-AND-FAILURE.md) | Memory ≠ truth; SFT |
| [V1 core spec](docs/spec/ANNE-V1-CORE.md) | Target V1.0 definition |
| [V1 gap analysis](docs/spec/ANNE-V1-GAP-ANALYSIS.md) | Honest implementation gaps |
| [Vitavolt / VITA](docs/applications/VITAVOLT-VITA.md) | Application boundary only |
| [Platform README (install, tree, examples)](docs/README-PLATFORM.md) | Continued technical sections from prior README |

---

For install, architecture tree, examples, citation, and legacy hardening notes, continue in **[docs/README-PLATFORM.md](docs/README-PLATFORM.md)**.
