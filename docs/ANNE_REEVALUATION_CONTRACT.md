# ANNE Re-Evaluation Contract

## Purpose

Re-evaluation is a bounded feedback path for knowledge whose provenance has
become invalid.

It does not erase history and it does not grant authority.

## Contract

1. An explicit evidence node is invalidated.
2. Downstream dependent nodes become `STALE`.
3. A caller must explicitly identify the stale target to re-evaluate.
4. A bounded research plan gathers fresh evidence.
5. Fresh evidence is independently verified against the stale target.
6. Only `VERIFIED` re-evaluation results may create an active replacement.
7. `UNVERIFIED`, `CONFLICTING`, and `REFUTED` results leave the stale target stale.
8. Historical nodes remain present and unchanged.
9. Fresh evidence remains `UNVERIFIED` in the Evidence Ledger unless an
   independent ledger-level status transition is explicitly established.
10. Re-evaluation does not grant action authority.

## Data-flow

```text
ACTIVE EVIDENCE
      |
      v
INVALIDATED
      |
      v
STALE DOWNSTREAM RESULT
      |
      v
BOUNDED RESEARCH
      |
      v
FRESH EVIDENCE
      |
      v
INDEPENDENT VERIFICATION
      |
  +---+-------------------+
  |                       |
VERIFIED            OTHER STATUS
  |                 (UNVERIFIED /
  v                  CONFLICTING /
REPLACEMENT           REFUTED)
  |                       |
  v                       v
RE-SYNTHESIS          REMAIN STALE
```

The replacement is a new provenance node linked to the fresh evidence and to
the historical stale node with a `replaces` edge. The old node is never
rewritten or deleted.

## Safety boundary

Re-evaluation is epistemic maintenance, not authorization.

A verified replacement may update the cognitive state and synthesis, but it
does not bypass `AgencyGate`, `EvidenceGate`, or any downstream action policy.