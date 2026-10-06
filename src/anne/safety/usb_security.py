"""USB-bound startup gate for the local ANNE runtime.

This is an authorization boundary for launching ANNE, not a claim that a
normal USB flash drive is a tamper-proof hardware security module. The gate
binds a local installation to a secret token stored on the owner's USB
device and, when configured, the device identity.

For stronger protection, a future hardware-backed provider should use a
challenge-response security key (for example a platform/HSM-backed key)
instead of a copyable token file.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_KEY_FILENAME = ".anne_authorization.json"


@dataclass(frozen=True)
class UsbAuthorization:
    """Expected USB authorization material."""

    key_id: str
    secret_digest: str
    device_fingerprint: str | None = None


class UsbSecurityGate:
    """Fail-closed gate that requires the owner's USB authorization token."""

    def __init__(
        self,
        *,
        key_filename: str = DEFAULT_KEY_FILENAME,
        require_device_fingerprint: bool = True,
    ) -> None:
        self.key_filename = key_filename
        self.require_device_fingerprint = require_device_fingerprint

    @staticmethod
    def discover_mounts() -> tuple[Path, ...]:
        """Return conservative removable-media candidates.

        Platform-specific removable-device enumeration is intentionally kept
        out of the core gate. Callers may pass an explicitly selected USB
        mount, which is more reliable and avoids privileged hardware access.
        """
        return ()

    @staticmethod
    def device_fingerprint(mount: Path) -> str | None:
        """Best-effort local device identity; never treats a volume label as proof."""
        try:
            stat = mount.stat()
        except OSError:
            return None
        raw = f"{platform.system()}|{mount.resolve()}|{stat.st_dev}".encode()
        return hashlib.sha256(raw).hexdigest()

    def enroll(self, usb_mount: str | Path) -> Path:
        """Create authorization material on an owner's USB device."""
        mount = Path(usb_mount).expanduser().resolve()
        if not mount.is_dir():
            raise FileNotFoundError(f"USB mount is not available: {mount}")

        secret = secrets.token_bytes(32)
        key_id = secrets.token_hex(16)
        payload = {
            "version": 1,
            "key_id": key_id,
            "secret": secret.hex(),
            "device_fingerprint": self.device_fingerprint(mount),
        }
        target = mount / self.key_filename
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        return target

    def verify(
        self,
        usb_mount: str | Path,
        *,
        expected_key_id: str | None = None,
    ) -> UsbAuthorization:
        mount = Path(usb_mount).expanduser().resolve()
        token_path = mount / self.key_filename
        if not token_path.is_file():
            raise PermissionError("ANNE authorization USB token is missing")

        try:
            payload: dict[str, Any] = json.loads(
                token_path.read_text(encoding="utf-8")
            )
            secret = bytes.fromhex(str(payload["secret"]))
            key_id = str(payload["key_id"])
            enrolled_fingerprint = payload.get("device_fingerprint")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise PermissionError("ANNE authorization token is invalid") from exc

        if expected_key_id is not None and not hmac.compare_digest(key_id, expected_key_id):
            raise PermissionError("ANNE authorization key ID mismatch")

        current_fingerprint = self.device_fingerprint(mount)
        if (
            self.require_device_fingerprint
            and enrolled_fingerprint
            and current_fingerprint != enrolled_fingerprint
        ):
            raise PermissionError("ANNE authorization device mismatch")

        digest = hashlib.sha256(secret).hexdigest()
        return UsbAuthorization(
            key_id=key_id,
            secret_digest=digest,
            device_fingerprint=current_fingerprint,
        )

    def require(self, usb_mount: str | Path, *, expected_key_id: str | None = None) -> UsbAuthorization:
        """Fail closed if the authorized USB device is not present."""
        return self.verify(usb_mount, expected_key_id=expected_key_id)


__all__ = ["UsbAuthorization", "UsbSecurityGate"]
