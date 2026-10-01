# ANNE Agentic Safety Evaluation

## Purpose

This evaluation layer tests a narrow engineering question:

> Can ANNE prevent a manipulated or insufficiently verified model output from becoming authorized external action?

It is intentionally **non-harmful and synthetic**. It does not reproduce biological, cyber, weapons, or other operationally harmful instructions.

## Threat-model classes

The first evaluation matrix covers:

1. authority spoofing;
2. memory poisoning;
3. tool-permission escalation;
4. instruction-hierarchy manipulation;
5. false or incomplete verification;
6. conflicting evidence;
7. stale or superseded context;
8. recovery after invalidation.

## Current control mapping

| Threat class | ANNE control | Expected boundary |
|---|---|---|
| Authority spoofing | AgencyGate + authority metadata | REVIEW |
| Memory poisoning | verification gate | DENY |
| Tool escalation | explicit authority + side-effect gate | REVIEW |
| Instruction manipulation | safety policy gate | DENY |
| Verification failure | factual verification gate | DENY |
| Conflicting evidence | verification state | DENY |
| Stale context | re-verification requirement | DENY |
| Invalidation/recovery | bounded review/revalidation | REVIEW |

These are **control expectations**, not evidence of universal safety.

## Evaluation design

The intended empirical comparison is:

```
BASE MODEL / AGENT
        vs
BASE MODEL / AGENT + ANNE
```

using the same non-harmful synthetic scenarios.

Primary metrics:

- unauthorized-action rate;
- false acceptance;
- false rejection;
- provenance coverage;
- verification-gate activation;
- recovery success;
- repeated-error rate;
- human-review frequency.

## Current status

The repository currently contains deterministic regression tests for the AgencyGate boundary. These tests establish implementation behavior for the listed synthetic cases.

They do **not** establish:

- resistance to real-world jailbreaks;
- safety of a specific external model;
- general agentic safety;
- independent held-out security performance;
- production or regulatory certification.

The next step is a reproducible held-out scenario suite with explicit attack variants, baseline comparisons, and published result artifacts.

## Safety invariant

The core invariant under evaluation is:

```text
MODEL OUTPUT       ≠ AUTHORIZED INTENT
MEMORY             ≠ AUTHORITY
TOOL PROPOSAL      ≠ TOOL PERMISSION
RESEARCH RESULT    ≠ VERIFIED FACT
VERIFIED FACT      ≠ EXECUTION AUTHORITY
LEARNED STRATEGY   ≠ AUTOMATIC PERMISSION
```

ANNE should remain fail-closed when required evidence, provenance, safety approval, or authority is missing.
