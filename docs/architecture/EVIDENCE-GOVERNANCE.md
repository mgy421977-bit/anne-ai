# Evidence governance

## Target flow

```text
SEARCH → CANDIDATE EVIDENCE → UNVERIFIED
      → INDEPENDENT VERIFICATION
      → VERIFIED | AVAILABLE | REFUTED | CONFLICTING
      → DECISION
```

## Principles

1. A search hit is **candidate evidence**, not verified knowledge.
2. Default stance for new claims is **UNVERIFIED**.
3. Memory retrieval is **reference**, not proof (`EvidenceGate` + tests on required paths).
4. `requires_evidence=False` is for non-factual or non-evidence-required interactions (e.g. greetings)—not a general bypass for factual claims.
5. ANLA participates as a **decision gate / heuristic layer**; independent verification is a **separate** concern.

## CURRENT

- `src/anne/core/evidence.py` — EvidenceGate
- `src/anne/core/verification.py` — factual status contracts
- `tests/test_evidence_enforcement.py` — unverified memory must not enable authoritative decision when evidence is required

## TARGET

Unify research → package → verification → decision on factual missions without elevating MITOS candidates to verified knowledge.
