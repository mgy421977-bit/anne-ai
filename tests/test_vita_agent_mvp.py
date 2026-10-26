from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from anne.core.agency_gate import ActionDecision
from tools.anne_vita_agent.runner import LocalAgent
from tools.anne_vita_agent.vita_adapter import (
    DockerVitaAdapter,
    VitaAdapterError,
    VitaSolarRequest,
)


class FakeAnne:
    def __init__(self, status: str = "EXECUTED") -> None:
        self.status = status
        self.calls = 0

    def run_cognitive(self, text: str):
        self.calls += 1
        return SimpleNamespace(status=self.status, reason="test", stage_trace=("DUY", "ANLA"))


class FakeVita:
    def __init__(self):
        self.calls = []

    def calculate_ges(self, payload):
        self.calls.append(payload)
        return {"result_type": "test-double", "result": {"capacity_kw": 1.0}}


def sample_task():
    return {
        "action": "vita.ges_precheck",
        "input": {
            "location": "Izmir",
            "roof_area_m2": 200,
            "daily_consumption_kwh": 150,
        },
    }


def test_vita_request_rejects_nonpositive_and_extreme_values():
    with pytest.raises(ValueError):
        VitaSolarRequest.from_mapping({**sample_task()["input"], "roof_area_m2": 0})
    with pytest.raises(ValueError):
        VitaSolarRequest.from_mapping(
            {**sample_task()["input"], "daily_consumption_kwh": 1_000_001}
        )


def test_unknown_action_is_denied_without_running_adapters(tmp_path):
    anne, vita = FakeAnne(), FakeVita()
    agent = LocalAgent(workspace=tmp_path, vita_adapter=vita, anne_runtime=anne)
    result = agent.run({"action": "shell.exec", "input": {"command": "whoami"}})
    assert result["status"] == "DENIED"
    assert anne.calls == 0
    assert vita.calls == []


def test_invalid_vita_input_is_rejected_before_anne(tmp_path):
    anne, vita = FakeAnne(), FakeVita()
    agent = LocalAgent(workspace=tmp_path, vita_adapter=vita, anne_runtime=anne)
    invalid = sample_task()
    invalid["input"]["roof_area_m2"] = 0
    with pytest.raises(ValueError):
        agent.run(invalid)
    assert anne.calls == 0
    assert vita.calls == []


def test_anne_blocking_status_prevents_vita_call(tmp_path):
    anne, vita = FakeAnne("ABORTED"), FakeVita()
    agent = LocalAgent(workspace=tmp_path, vita_adapter=vita, anne_runtime=anne)
    result = agent.run(sample_task())
    assert result["status"] == "BLOCKED_BY_ANNE"
    assert vita.calls == []


def test_unknown_anne_status_fails_closed(tmp_path):
    anne, vita = FakeAnne("UNKNOWN"), FakeVita()
    agent = LocalAgent(workspace=tmp_path, vita_adapter=vita, anne_runtime=anne)
    result = agent.run(sample_task())
    assert result["status"] == "BLOCKED_BY_ANNE"
    assert vita.calls == []


def test_allowlisted_calculation_passes_agency_gate_and_calls_adapter(tmp_path):
    anne, vita = FakeAnne(), FakeVita()
    agent = LocalAgent(workspace=tmp_path, vita_adapter=vita, anne_runtime=anne)
    result = agent.run(sample_task())
    assert result["status"] == "COMPLETED"
    assert result["agency_gate"]["decision"] == ActionDecision.ALLOW.value
    assert len(vita.calls) == 1
    assert result["sandbox"]["arbitrary_code_execution"] is False


def test_docker_adapter_uses_restricted_container_flags(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.anne_vita_agent.vita_adapter.shutil.which", lambda _: "docker")

    def fake_run(command, **kwargs):
        assert "--network" in command and command[command.index("--network") + 1] == "none"
        assert "--read-only" in command
        assert "--cap-drop=ALL" in command
        assert "--pull=never" in command
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 25
        payload = {
            "capacity_kw": 12.4,
            "num_panels": 20,
            "annual_kwh": 17980,
            "bom": {},
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload) + chr(10), stderr="")

    monkeypatch.setattr("tools.anne_vita_agent.vita_adapter.subprocess.run", fake_run)
    result = DockerVitaAdapter(tmp_path).calculate_ges(sample_task()["input"])
    assert result["result_type"] == "preliminary_estimate"
    assert result["result"]["capacity_kw"] == 12.4


def test_docker_adapter_rejects_vita_error_payload(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.anne_vita_agent.vita_adapter.shutil.which", lambda _: "docker")
    monkeypatch.setattr(
        "tools.anne_vita_agent.vita_adapter.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, stdout='{"error":"Product not found"}' + chr(10), stderr=""
        ),
    )
    with pytest.raises(VitaAdapterError, match="Product not found"):
        DockerVitaAdapter(tmp_path).calculate_ges(sample_task()["input"])


def test_docker_adapter_fails_closed_when_docker_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.anne_vita_agent.vita_adapter.shutil.which", lambda _: None)
    with pytest.raises(VitaAdapterError, match="Docker CLI not found"):
        DockerVitaAdapter(tmp_path).calculate_ges(sample_task()["input"])
