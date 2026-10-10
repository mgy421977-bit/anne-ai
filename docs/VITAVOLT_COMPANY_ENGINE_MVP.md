# ANNE Company Engine — Vitavolt MVP

**Status:** MVP implementation proposal / initial code, not a deployed sales automation.

## Objective

Use ANNE's cognitive orchestration as a founder-facing operating layer for Vitavolt Global, initially focused on AI infrastructure energy solutions. The MVP tracks work, enforces task dependencies, records outcomes locally, and prepares action proposals for human review.

## Architecture boundary

```text
Founder objective
      |
      v
Vitavolt Company Engine
  - starter task graph
  - dependency-aware queue
  - persistent SQLite progress
  - evidence-bearing action proposals
      |
      v
Founder review / ANNE Agency Gate
      |
      v
Future integrations (separately implemented and authorized)
  - public-source prospect research
  - CRM / pipeline
  - proposal and technical model generation
  - approved outreach
```

This first slice is deliberately deterministic. It does not yet call MITOS or a hosted model, scrape websites, send messages, change a CRM, or execute external actions. Those integrations must use the canonical ANNE runtime and pass the existing agency/safety policy.

## Starter workflow

1. Map AI infrastructure energy demand and target segments.
2. Define Vitavolt's PV, BESS, EMS and resilience engineering offer.
3. Establish target-account qualification criteria.
4. Build a prospect list from public evidence and retain source URLs.
5. Prepare discovery questions and a technical qualification pack.
6. Create a transparent preliminary energy model with explicit assumptions.
7. Draft tailored outreach for founder review; never auto-send.
8. Review pipeline, evidence gaps and next decisions.

Dependencies are enforced: a task cannot be marked complete before its prerequisite tasks are complete. Existing progress is not overwritten when the starter plan is seeded again.

## Run

Requires the repository's supported Python environment (Python 3.12+).

```bash
python -m anne.applications.vitavolt_company_engine
```

The default database is `.anne/vitavolt_company_engine.sqlite3`. Keep this local database out of version control; it may contain business context. Override it with `--db /path/to/file.sqlite3`.

Run tests:

```bash
pytest -q tests/test_vitavolt_company_engine.py
```

## Agency and evidence rules

- Action proposals remain `PENDING_APPROVAL`; this module contains no executor.
- A proposal requires explicit scope, reason, evidence, risk, validation and rollback.
- Public-source facts should retain source URLs and retrieval dates in future integrations.
- Unknowns must remain unknown; no fabricated prospects, prices, energy yields or ROI.
- Sending outreach, publishing content, changing external systems or spending money requires separate explicit authorization and an implementation that enforces ANNE's Agency Gate.
- Do not place API keys or prospect personal data in source control.

## Next milestones

1. Run unit tests in CI and review the branch diff.
2. Connect this task graph to the canonical ANNE runtime without duplicating memory or agency policy.
3. Add evidence-backed public prospect research with source provenance.
4. Add a founder-facing report of completed work, blockers, and decisions needed.
5. Integrate CRM and outreach only after the approval boundary is tested end-to-end.
