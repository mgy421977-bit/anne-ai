# MITOS Cloud Quantum Field — Phase 1

## Purpose

The Cloud Quantum Field is an ANNE-integrated, cloud-hosted computation layer
for MITOS. It uses classical distributed computation and a quantum-inspired
complex-amplitude model to explore candidate relationships. It is not a
physical quantum computer and makes no quantum-advantage claim.

## Architecture boundary

- MITOS creates candidate hypotheses.
- Cloud Quantum Field evaluates bounded candidate scores and computes a
  reproducible interference-inspired distribution.
- ANNE's existing CandidateSelector remains the independent selection gate.
- EvidenceGate and AgencyGate retain verification and action authority.
- Field outputs are proposals only; they are not facts, evidence, or permission.

## Phase 1 implementation

`anne.mythos.cloud_field` defines:
- `WorkerBackend`: pluggable execution contract for local or remote workers.
- `ThreadWorkerBackend`: bounded local reference backend.
- `CloudQuantumField`: deterministic phase assignment, complex amplitudes,
  interference-inspired weighting, and normalized probabilities.
- Immutable result/state records with an explicit `PROPOSAL_ONLY` authority.

The current backend is local threaded execution used as a reference adapter.
No cloud provider, network transport, persistent storage, daemon, or autoscaling
has been configured in this phase.

## Reproducibility and safety

- A caller-provided seed and candidate IDs determine phase values.
- Candidate IDs must be unique within a field.
- Scores must be finite numeric values in [0, 1]; booleans are rejected.
- The field has no tool access, external side effects, or action authority.
- Results must still pass ANNE's independent selector and evidence/agency gates.

## Next steps

1. Add a remote worker adapter behind `WorkerBackend`.
2. Add a durable experiment/state-seal store with schema versioning.
3. Integrate the field as an optional MITOS evaluation stage without bypassing
   CandidateSelector.
4. Benchmark quality, latency, memory, worker communication, and cost against
   classical baselines using reproducible workloads.
