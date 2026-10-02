# A3 ANLA Context-Consistency Contract Audit

**Date:** 2026-10-02  
**Type:** Research / engineering decision log (no implementation)  
**Status:** Contract definition proposed; implementation intentionally deferred

## Decision

Do not modify ANLA implementation until the A3 context-consistency contract is expressed as falsifiable tests.

The independent audit confirmed that ANLA is connected to the runtime pipeline and covered by the main test suite, but the current `C_ctx` implementation does not satisfy the documented A3 contract:

> `C_ctx` is defined as context consistency / overlap between the candidate and the DUY input.

The current implementation accepts only the candidate text and derives `C_ctx` from candidate word count. The repository already contains `token_overlap(a, b)`, but `context_consistency()` does not use it.

## Evidence chain

Expected:

```
DUY input + candidate
        ↓
      C_ctx
        ↓
 S_ANLA = αC_ctx + βC_log + γC_trace
```

Current:

```
candidate
   ↓
C_ctx(candidate)       C_log(candidate)
   ↓                         ↓
       S_ANLA + C_trace(candidate, failures)
```

The current pipeline passes the hypothesis claim to ANLA; the original DUY input is not independently supplied to `context_consistency()`.

## A3 v0.1 contract to test

The first implementation target remains deliberately bounded. A3 v0.1 should use the documented token/lemma-overlap approach; stronger semantic backends belong to the later Phase B work.

### Required properties

1. **Relevant candidate:** given a DUY input and a candidate that shares the relevant lexical/lemma content, `C_ctx` should be materially higher than for an unrelated candidate.
2. **Input sensitivity:** keeping the candidate fixed while changing the DUY input to an unrelated topic must be able to change `C_ctx`.
3. **Unrelated candidate:** a syntactically well-formed but unrelated candidate must not receive a high context score merely because it is long.
4. **Paraphrase boundary:** v0.1 may remain lexical/lemma based; semantic equivalence beyond that boundary must not be claimed until a stronger backend exists.
5. **Empty input/candidate:** behavior must be deterministic and fail-safe.
6. **Trace separation:** `C_trace` remains responsible for candidate ↔ failure-trace relation; it must not be silently conflated with `C_ctx`.
7. **Evidence separation:** ANLA remains a semantic/consistency gate and must not be treated as factual verification.
8. **Authority separation:** ANLA PASS must not authorize an action independently of the existing authority/agency gates.

## Minimum falsifiable test matrix

| Case | Expected contract |
|---|---|
| Same input + relevant candidate | higher `C_ctx` |
| Same input + unrelated candidate | lower `C_ctx` |
| Same candidate + unrelated input | `C_ctx` changes materially |
| Empty input | deterministic safe result |
| Empty candidate | `C_ctx = 0` |
| Candidate with high word count but unrelated topic | must not score high solely due to length |
| Existing failure trace + candidate | trace effect remains isolated to `C_trace` |

## Explicit non-goals

- No embedding or NLI backend in A3.
- No factual-truth verifier inside ANLA.
- No change to Agency Gate semantics.
- No unbounded retry behavior.
- No benchmark claim from the existing 30-example lexical fixture.

## Follow-up implementation boundary

Only after this contract is accepted should implementation change the ANLA API so that the context component receives the DUY input and candidate separately, then add the corresponding unit and pipeline integration tests.

The implementation should remain minimal and deterministic, using the existing tokenization/overlap primitive where appropriate.

## Audit conclusion

**A3 runtime integration: implemented.**  
**A3 documented C_ctx contract: not yet satisfied.**  
**Next action: contract tests first; implementation second.**
