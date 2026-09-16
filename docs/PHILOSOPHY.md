# ANNE research discipline and boundaries

ANNE is a **research system, not an AGI claim**. This repository deliberately
distinguishes implemented engineering from experiments, hypotheses, and future
research.

## What ANNE V1 is

- A cognitive orchestration prototype where **decisions live in Python runtime**
  (epistemic policy, comparison, revision, experience recording).
- Language models are a **LanguageInterface only**: they express ANNE’s already
  decided content; they do not own research, comparison, or authority.
- Local / external durable memory for factual answers and problem-solving
  experiences, with optional user isolation for demo sessions.

## What ANNE V1 is not

- ANNE is **not AGI**. There is no claim of human-level understanding,
  general autonomy, or unsupervised high-stakes decision making.
- ANNE is not a multi-agent swarm, CRM, or business automation product in V1.
- ANNE does not treat model brand names (“ChatGPT said”, “Gemini said”) as
  independent authority in user-facing answers.

## Reliability and safety layer

- Safety and character-integrity gates constrain learning that would degrade
  core ethical baselines (where implemented).
- API keys and secrets are configuration-only; they must never be stored in the
  memory database.
- Anonymous experience sharing is **off by default** (`ANNE_SHARE_EXPERIENCE`);
  when enabled it may only emit sanitized, non-content telemetry.

## Memory and learning

- Factual interactions and experience patterns are stored separately.
- V1 previous-answer recall is **exact-match** and deterministic.
- External memory roots (`ANNE_MEMORY_ROOT`) are storage only; they do not
  transfer cognitive authority.

## Benchmarks and evidence

- Benchmarks and decision logs document what was measured, not what is asserted
  as general intelligence.
- Prefer reproducible tests over narrative claims.

See also the repository README for setup and the V1 web path.
