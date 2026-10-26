# ANNE + VITA Local Agent — MVP Design and Audit

**Status:** implementation scaffold on a feature branch. Tests are authored but must be run in a Windows checkout before this MVP is considered verified.

## Repository audit (2026-10-26)

### ANNE AI

- Canonical research platform: https://github.com/mgy421977-bit/anne-ai
- Main branch inspected at commit b0af6695a50274105fe317e7973ce91adb7b6503.
- Existing components include AnneRuntime, DecisionLoop, CognitiveOrchestrator, AgencyGate, FractalMemory, and bounded research/verification components.
- AgencyGate fails closed when required action metadata or provenance is missing.
- Existing ANNE components do not themselves provide a hardened operating-system sandbox. This MVP uses the cognitive runtime for an assessment trace and AgencyGate for the allowlisted action decision.

### VITA Engine

- Repository: https://github.com/mgy421977-bit/VITA-Engine
- Main branch inspected at commit c58b7ef16cbb4a0d904e07db30da49772843cbe4.
- The repository contains energy/solar/solar_engine.py, which exposes SolarEngine.calculate_ges(location, roof_area_m2, daily_consumption_kwh, panel_code, inverter_code).
- Its calculation uses a local JSON product database and includes simplified production, investment, ROI, and BOM estimates. The source itself describes investment/ROI as rough estimates. Treat output as preliminary only.
- The adapter defaults to panel code PAN-CW-M12-132TNB-TOPCON, present in the inspected panel catalog, and inverter code INV-HUA-100-001, documented by the VITA README. A local run must still confirm both records resolve in the checked-out catalog.
- This adapter targets the Python VITA-Engine repository, not the separate browser-side JavaScript engine used by the Vitavolt website. The production web calculator is not modified.

## MVP contract

The CLI accepts one structured JSON task:

    {
      "action": "vita.ges_precheck",
      "input": {
        "location": "Izmir",
        "roof_area_m2": 200,
        "daily_consumption_kwh": 150
      }
    }

Only the action vita.ges_precheck is allowlisted. The task runner does not execute arbitrary commands, generated code, plugins, or network research. One request performs at most one VITA calculation. ANNE must return the explicit EXECUTED status or the VITA action is not invoked.

## Isolation controls

The adapter invokes Docker with:

- --pull=never (no implicit image pull);
- --network none;
- read-only container root and VITA source mount;
- dropped Linux capabilities and no-new-privileges;
- non-root container user;
- process, memory, CPU, temporary-storage and execution-time limits;
- shell=False and a fixed worker program (task text is data, never executable code).

Docker Desktop and a locally available python:3.12-slim image are prerequisites. The host Docker daemon and its configuration remain part of the trust boundary; this is not a claim of formal sandbox certification.

## Known limits / next work

1. This MVP does not contain an LLM planner, general web researcher, self-modifying code agent, or autonomous deployment.
2. The ANNE cognitive trace is observational and is not proof of truth or engineering correctness.
3. Docker integration tests use a mocked subprocess. No real Docker run, Windows integration run, or VITA calculation has been executed by this commit.
4. Before production use, verify catalog codes against the local VITA checkout and run end-to-end tests on Windows with Docker Desktop.
5. Future changes should add one capability at a time, benchmark it, and keep production calculator paths unchanged.

## Local setup

From the ANNE AI repository root in PowerShell:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"
    docker version
    docker image inspect python:3.12-slim
    pytest -q tests\test_vita_agent_mvp.py

The adapter does not install or pull Docker images automatically. If the image is missing, run docker pull python:3.12-slim manually before testing.

Example invocation (adjust the VITA repository path):

    @'
    {
      "action": "vita.ges_precheck",
      "input": {
        "location": "Izmir",
        "roof_area_m2": 200,
        "daily_consumption_kwh": 150
      }
    }
    '@ | python -m tools.anne_vita_agent --vita-root C:\src\VITA-Engine --workspace .\.anne-agent-workspace
