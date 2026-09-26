# Platform technical README

> Continuation of the root [README.md](../README.md). AGI / discovery positioning remains in the root README.

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

## Architecture at a glance

See also [docs/architecture/ANNE-COGNITIVE-ARCHITECTURE.md](architecture/ANNE-COGNITIVE-ARCHITECTURE.md) and [COGNITIVE-LOOP.md](architecture/COGNITIVE-LOOP.md).

```text
                    ┌──────────────────────┐
                    │   Model Provider     │
                    │ local / API / LLM    │
                    └──────────┬───────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────┐
│                    ANNE Cognitive Runtime                 │
│  FAILFAST → DUY → BAK → AMBIGUITY → GÖR → MITOS → SELECT│
│            → ANLA → EVIDENCE → HİSSET → AGENCY → YAP     │
│  Memory · Failure traces · EvidenceGate · AgencyGate     │
└──────────────────────────────────────────────────────────┘
```

## Install (research preview)

```bash
git clone https://github.com/mgy421977-bit/anne-ai.git
cd anne-ai
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e .
```

Optional extras (only when needed):

```bash
pip install -e ".[gemini]"     # Gemini SDK
pip install -e ".[cloud]"      # additional cloud providers
```

Base install is local-first; cloud SDKs are optional.

## Quick start

```python
from anne.agent.offline import create_offline_agent

agent = create_offline_agent()
# Prefer DecisionLoop / CognitiveOrchestrator paths documented in examples/
```

See `examples/` for pipeline and decision-loop demos.

## Tests

```bash
pytest tests/ -q
```

CI on `main` may be incomplete; treat green local tests as the current verification baseline.

## Key packages

| Path | Role |
|------|------|
| `src/anne/core/` | Pipeline, orchestrator, evidence, verification, agency |
| `src/anne/mythos/` | Candidate / hypothesis generation |
| `src/anne/memory/` | Fractal memory |
| `src/anne/providers/` | Local / API model backends |
| `src/anne/agent/` | Agent runtime entry |
| `tests/` | Unit and contract tests |

## Honesty constraints

- Feature-branch research (price intelligence, language curriculum, VITA adapter) is **not** claimed as `main` production capability.
- ANLA is a decision gate / heuristic layer, not a full independent verification product.
- Agency is implemented as modules; unified single-path runtime is a V1.0 target.

## Citation

```bibtex
@software{anne_ai_2026,
  author       = {Yılmaz, Mustafa Gökhan},
  title        = {ANNE – Adaptive Neural Nexus Engine},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/mgy421977-bit/anne-ai},
  orcid        = {0009-0002-6591-0163}
}
```

## License

Apache License 2.0 — see [`LICENSE`](../LICENSE).

**Author:** Mustafa Gökhan Yılmaz · ORCID [0009-0002-6591-0163](https://orcid.org/0009-0002-6591-0163) · İzmir, Türkiye
