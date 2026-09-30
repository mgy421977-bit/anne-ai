# ANNE Metacognition Contract

## Purpose

Metacognition evaluates the recorded reasoning process. It records what is explicitly known, what remains uncertain, which evidence and decision dependencies were recorded, and whether further research or review is indicated.

Metacognition is observational. It does not establish truth, causality, authority, or permission to execute an action.

## Inputs

The evaluator reads only explicit fields from a CycleTrace:

- verification status and verification sources;
- decision reason;
- intent;
- hypotheses;
- learning observations;
- stop reason.

It does not infer missing facts from confidence, semantic similarity, timestamps, strategy names, or outcomes.

## Outputs

MetacognitiveAssessment records:

- known;
- unknown;
- evidence_basis;
- assumptions;
- decision_dependencies;
- recalibration_triggers;
- evaluation_status;
- research_required;
- research_reason.

`evaluation_status` is `PROCESS_REVIEW_REQUIRED` when the recorded process has an explicit review gap such as missing intent, missing decision rationale, or an unresolved factual status. Otherwise it is `PROCESS_COMPLETE`.

`research_required` is true when verification is `UNVERIFIED`, `CONFLICTING`, or `REFUTED`. This is a research/reassessment signal, not a truth assertion.

## Safety boundary

```text
Metacognition
    ↓
process observation
    ↓
uncertainty / missing-prerequisite detection
    ↓
research or review signal

Metacognition
    ✕
truth certification
authority
causal attribution
action authorization
```

A metacognitive assessment must not bypass EvidenceGate, Verification, AgencyGate, or any other safety boundary.

## Recalibration

Recalibration triggers are explicit observations such as:

- `new_independent_evidence`
- `provenance_completion`
- `intent_clarification`
- `decision_reason_recording`

The trigger itself does not execute research or an action. A bounded planner or runtime component must separately decide whether and how to act on it.
