"""Docker-isolated adapter for the existing VITA-Engine solar calculator."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_IMAGE = "python:3.12-slim"
MAX_ROOF_AREA_M2 = 100_000.0
MAX_DAILY_CONSUMPTION_KWH = 1_000_000.0
DEFAULT_PANEL_CODE = "PAN-CW-M12-132TNB-TOPCON"
DEFAULT_INVERTER_CODE = "INV-HUA-100-001"

# Fixed worker program. User task text is never interpolated into executable code.
_WORKER = r"""
import json, sys
sys.path.insert(0, "/opt/vita")
from energy.solar.solar_engine import SolarEngine
p = json.load(sys.stdin)
result = SolarEngine().calculate_ges(
    location=p["location"],
    roof_area_m2=p["roof_area_m2"],
    daily_consumption_kwh=p["daily_consumption_kwh"],
    panel_code=p["panel_code"],
    inverter_code=p["inverter_code"],
)
print(json.dumps(result, ensure_ascii=False, allow_nan=False))
"""


class VitaAdapterError(RuntimeError):
    """The isolated VITA process failed or returned an invalid result."""


@dataclass(frozen=True)
class VitaSolarRequest:
    location: str
    roof_area_m2: float
    daily_consumption_kwh: float
    panel_code: str = DEFAULT_PANEL_CODE
    inverter_code: str = DEFAULT_INVERTER_CODE

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "VitaSolarRequest":
        if not isinstance(value, dict):
            raise ValueError("input must be a JSON object")
        location = value.get("location")
        if not isinstance(location, str) or not location.strip() or len(location) > 120:
            raise ValueError("location must be a non-empty string of at most 120 characters")

        def positive_number(key: str, maximum: float) -> float:
            raw = value.get(key)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"{key} must be a number")
            number = float(raw)
            if number <= 0 or number > maximum:
                raise ValueError(f"{key} must be greater than 0 and at most {maximum:g}")
            return number

        def product_code(key: str, default: str) -> str:
            raw = value.get(key, default)
            if not isinstance(raw, str) or not raw or len(raw) > 100:
                raise ValueError(f"{key} must be a non-empty product code")
            allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            if any(ch not in allowed for ch in raw):
                raise ValueError(f"{key} contains unsupported characters")
            return raw

        return cls(
            location=location.strip(),
            roof_area_m2=positive_number("roof_area_m2", MAX_ROOF_AREA_M2),
            daily_consumption_kwh=positive_number(
                "daily_consumption_kwh", MAX_DAILY_CONSUMPTION_KWH
            ),
            panel_code=product_code("panel_code", DEFAULT_PANEL_CODE),
            inverter_code=product_code("inverter_code", DEFAULT_INVERTER_CODE),
        )


class DockerVitaAdapter:
    """Run one allowlisted VITA calculation in a restricted Docker container.

    Docker and the configured image must already be installed locally. This adapter
    never pulls images, enables network access, or invokes a shell.
    """

    def __init__(
        self,
        vita_root: str | Path,
        *,
        image: str = DEFAULT_IMAGE,
        timeout_seconds: int = 25,
        docker_executable: str = "docker",
    ) -> None:
        root = Path(vita_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("vita_root must be a directory")
        if "," in str(root):
            raise ValueError("vita_root path cannot contain commas for Docker mount syntax")
        if not image or any(ch.isspace() for ch in image):
            raise ValueError("image must be a non-empty image reference without whitespace")
        if timeout_seconds < 1 or timeout_seconds > 120:
            raise ValueError("timeout_seconds must be between 1 and 120")
        self.vita_root = root
        self.image = image
        self.timeout_seconds = timeout_seconds
        self.docker_executable = docker_executable

    def calculate_ges(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = VitaSolarRequest.from_mapping(payload)
        if shutil.which(self.docker_executable) is None:
            raise VitaAdapterError(
                "Docker CLI not found. Install Docker Desktop and verify docker version."
            )

        container_input = {
            "location": request.location,
            "roof_area_m2": request.roof_area_m2,
            "daily_consumption_kwh": request.daily_consumption_kwh,
            "panel_code": request.panel_code,
            "inverter_code": request.inverter_code,
        }
        command = [
            self.docker_executable, "run", "--rm", "--pull=never",
            "--network", "none", "--read-only", "--pids-limit=64",
            "--memory=512m", "--cpus=1",
            "--security-opt=no-new-privileges", "--cap-drop=ALL",
            "--user", "65534:65534",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "--mount", f"type=bind,source={self.vita_root},target=/opt/vita,readonly",
            "--workdir", "/opt/vita",
            self.image, "python", "-c", _WORKER,
        ]
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(container_input, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VitaAdapterError("VITA calculation timed out") from exc
        except OSError as exc:
            raise VitaAdapterError(f"Could not start Docker: {exc}") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "no container output").strip()
            raise VitaAdapterError(
                f"VITA container failed (exit {completed.returncode}): {detail[-1200:]}"
            )
        lines = (completed.stdout or "").strip().splitlines()
        if not lines:
            raise VitaAdapterError("VITA container returned no JSON result")
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise VitaAdapterError("VITA container returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise VitaAdapterError("VITA result must be a JSON object")
        if result.get("error"):
            raise VitaAdapterError(f"VITA rejected the request: {result['error']}")
        required = {"capacity_kw", "num_panels", "annual_kwh", "bom"}
        missing = sorted(required.difference(result))
        if missing:
            raise VitaAdapterError(f"VITA result missing required fields: {', '.join(missing)}")

        return {
            "engine": "VITA-Engine SolarEngine.calculate_ges",
            "result_type": "preliminary_estimate",
            "inputs": container_input,
            "result": result,
            "limitations": [
                "VITA source describes investment and ROI calculations as rough estimates.",
                "This output is not a final engineering design, quotation, or site survey.",
            ],
        }
