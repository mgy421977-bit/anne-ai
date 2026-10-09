# ANNE engineering calculation core — initial scope

## Decision
For the initial Vitavolt workflow, ANNE owns the preliminary deterministic PV/BESS
calculations. VITA Engine remains a future downstream engineering integration and
is not required to run these first calculations.

## Current scope
- Rooftop PV geometric screening from explicitly supplied roof area, panel power,
  panel dimensions and usable roof fraction.
- Optional production, annual-energy ceiling, savings and simple-payback estimates
  only when their required inputs are explicitly supplied.
- BESS usable-energy and constant-load runtime screening with power-limit checks.
- Input validation, explicit missing inputs, assumptions and warnings.

## Runtime integration and durable rules
The OpenRouter tool interface exposes this layer as `engineering_calculate`.
The tool is registered in ANNE's allowlist and still passes through the existing
AgencyGate authorization path. It is read-only and has no external side effects.

The following are durable architecture rules, not optional prompting preferences:
1. Arithmetic is performed by deterministic Python formulas, not guessed by an LLM.
2. Preserve inputs, units, outputs, assumptions, missing inputs, warnings and status.
3. Never silently fill missing values with typical or plausible defaults.
4. Recompute when relevant inputs change; a remembered prior result is not a current result.
5. Keep calculations traceable and reproducible; invalid input must fail explicitly.
6. Persistent memory is contextual recall, not a substitute for recalculation or validation.

## Deliberate limits
- No invented yield, tariff, installed cost, hourly profile, self-consumption profile,
  export compensation, finance assumptions or engineering constraints.
- Annual production uses caller-supplied specific yield; it is not independently
  verified or site simulated.
- Self-consumption is an annual-energy upper bound, not an hourly energy model.
- Payback is simple and undiscounted; it excludes financing, O&M, degradation,
  replacement, tax and discounting.
- BESS runtime is a constant-load screening estimate, not a battery dispatch model.
- These outputs are not construction-ready design, bankable forecasts, or engineering
  sign-off. Human/qualified engineer review remains necessary.

## Verification
Run:
```bash
python -m pytest tests/unit/test_engineering_calculations.py -q
```
