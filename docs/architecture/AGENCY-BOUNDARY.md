# Agency boundary

## Intent

ANNE explores **agency constraints**: the right to *think* is not the right to *act*.

Human approval, when required, must not be silently bypassed. The goal is better **decision quality and visibility**, not removal of human responsibility.

## CURRENT modules

| Module | Role |
|--------|------|
| `src/anne/core/agency_gate.py` | Policy-style authorization (safety, verification status, provenance, risk, reversibility) |
| `src/anne/safety/agency_gate.py` | Explicit human approval records; execute only after APPROVE |

## TARGET

One coherent runtime path:

```text
cognition → evidence/verify → policy gate → (optional) human approval → action | deny
```

Until that path is universal, document agency as **implemented modules + integration gap**, not as a finished product guarantee.
