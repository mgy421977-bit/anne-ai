"""Safe GitHub release discovery for the offline ANNE desktop runtime."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MANIFEST_URL = os.environ.get(
    "ANNE_UPDATE_MANIFEST",
    "https://raw.githubusercontent.com/mgy421977-bit/anne-ai/main/desktop/release.json",
)


@dataclass(frozen=True)
class ReleaseManifest:
    version: str
    package_url: str
    sha256: str
    min_free_gb: float = 2.0

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ReleaseManifest":
        return cls(
            version=str(data["version"]),
            package_url=str(data["package_url"]),
            sha256=str(data["sha256"]).lower(),
            min_free_gb=float(data.get("min_free_gb", 2.0)),
        )


def fetch_manifest(url: str = DEFAULT_MANIFEST_URL, timeout: int = 8) -> ReleaseManifest:
    """Fetch only public release metadata; failure must not block offline startup."""
    request = urllib.request.Request(url, headers={"User-Agent": "ANNE-Updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return ReleaseManifest.from_dict(json.loads(response.read().decode("utf-8")))


def is_newer(current: str, available: str) -> bool:
    """Compare simple semantic versions without third-party dependencies."""
    def parts(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.lstrip("v").split("."))

    return parts(available) > parts(current)


def download_and_verify(manifest: ReleaseManifest, destination: Path, timeout: int = 120) -> Path:
    """Download a release package and verify its SHA-256 before exposing it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="anne-update-", suffix=".zip", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            manifest.package_url, headers={"User-Agent": "ANNE-Updater"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response, temporary.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest().lower()
        if digest != manifest.sha256:
            raise ValueError("ANNE update package failed SHA-256 verification")
        temporary.replace(destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def extract_verified_package(package: Path, target: Path) -> None:
    """Extract only after verification; reject path traversal entries."""
    target = target.resolve()
    with zipfile.ZipFile(package) as archive:
        for member in archive.infolist():
            candidate = (target / member.filename).resolve()
            if candidate != target and target not in candidate.parents:
                raise ValueError(f"unsafe update path: {member.filename}")
        target.mkdir(parents=True, exist_ok=True)
        archive.extractall(target)
