# External Research Provider Smoke Check

The smoke checker distinguishes adapter readiness from live provider availability.

Run from the repository root:

```bash
python benchmarks/scripts/check_research_providers.py
```

Interpretation:

- **configured=false**: the provider is intentionally dormant and ANNE fails closed.
- **configured=true, probe_succeeded=true**: the configured adapter returned valid bounded evidence.
- **configured=true, probe_succeeded=false**: configuration exists but the provider did not return valid evidence.
- Scrapling additionally reports whether its Python dependency is installed.

The checker never treats provider output as verified truth. Provider output remains
retrieval evidence and continues through ANNE's provenance and verification layers.

A successful synthetic adapter probe is **not** a real-world security or provider
availability guarantee. Agent-Reach and Patchright require their configured local
workers/commands. Scrapling's probe uses a deterministic fetch fixture to validate
the adapter contract without depending on an external website.
