# Cognitive loop — CURRENT vs TARGET

## TARGET (V1.0 design)

```text
FAILFAST → DUY → BAK → AMBIGUITY → GÖR → MITOS → SELECT
  → ANLA → EVIDENCE → INDEPENDENT VERIFICATION
  → HİSSET → AGENCY GATE → YAP | ABSTAIN
  → MEMORY → FAILURE TRACE → bounded NEXT CYCLE
```

## CURRENT on `main` (honest map)

| Stage | On main? | Notes |
|-------|----------|--------|
| FAILFAST | Yes | `fail_fast.py` / pipeline |
| DUY | Yes | Pipeline |
| BAK | Yes | Memory observation |
| AMBIGUITY | Yes | `ambiguity.py` + orchestrator |
| GÖR | Yes | Hypothesis attention |
| MITOS | Yes | Candidate generation (non-authoritative) |
| SELECT | Yes | Selection without mandatory synthesis |
| ANLA | Partial | Heuristic score + EvidenceGate hook — **not** a full independent verification engine |
| EVIDENCE | Partial | EvidenceGate; required-path blocking tested |
| INDEPENDENT VERIFICATION | Partial | Contracts exist; not a complete E2E product pipe on every path |
| HİSSET | Yes | Ethic / contextual scoring |
| AGENCY GATE | Partial | Two modules (`core` + `safety`); not always one unified path |
| YAP / ABSTAIN | Yes | Including evidence-blocked abstain paths |
| MEMORY | Yes | FractalMemory |
| FAILURE TRACE | Yes | SFT + recovery helpers |
| bounded NEXT CYCLE | Partial | Orchestrator retry / bounded outcomes |

**Do not read the TARGET diagram as a claim that every box is production-complete on main.**
