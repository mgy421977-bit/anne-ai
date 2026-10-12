# ANNE ↔ VITA-Engine Tool Bridge

## Status

A small optional Python bridge is implemented at `src/anne/tools/vita_engine.py` and registered as a guarded tool in `AnneAgent` when a trusted local VITA checkout is configured. It does not start a server or create a deployed/live connection by itself.

## Local setup

1. Check out VITA-Engine from a trusted source.
2. Install VITA-Engine's documented Python dependencies in the ANNE environment.
3. Set `VITA_ENGINE_PATH` to the absolute path of that checkout.
4. Instantiate `AnneAgent` with `vita_engine_path="/absolute/path/to/VITA-Engine"` (or set `VITA_ENGINE_PATH` before constructing the agent). The tool is then added to the agent's guarded tool registry and model tool schema.
5. Run end-to-end tests in the actual ANNE runtime before describing the connection as active.

Example:

```python
from anne.tools.vita_engine import VitaEngineTool

tool = VitaEngineTool()  # reads VITA_ENGINE_PATH
result = tool.execute({
    "request_id": "anne-vita-001",
    "operation": "carbon_assess",
    "input": {
        "reporting_year": 2025,
        "energy": [{
            "source": "electricity",
            "quantity": 1000,
            "unit": "kWh",
            "period": "2025",
            "data_quality": "invoiced"
        }]
    }
})
assert result["human_review_required"] is True
```

## Safety boundaries

- Only the VITA adapter's explicit operations are accepted.
- The bridge uses a local configured checkout; it does not download code.
- The configured checkout must be trusted because Python imports execute local code.
- VITA retains calculation ownership; ANNE should explain results, not rewrite calculated values.
- Human review remains mandatory for engineering, investment, ETS, and taxonomy decisions.
- Do not expose this bridge through a network service until authentication, authorization, rate limits, input-size limits, timeouts, audit logging, and deployment review are implemented.

## Not yet done

The bridge has not been registered into the full ANNE orchestration/tool-selection flow and has not been tested end-to-end against a configured VITA checkout. This PR adds the integration module and configuration tests only.
