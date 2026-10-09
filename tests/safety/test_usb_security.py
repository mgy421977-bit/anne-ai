from pathlib import Path

import pytest

from anne.safety.usb_security import UsbSecurityGate


def test_usb_gate_enrolls_and_verifies(tmp_path: Path) -> None:
    gate = UsbSecurityGate()
    gate.enroll(tmp_path)
    auth = gate.verify(tmp_path)
    assert auth.key_id
    assert auth.secret_digest


def test_usb_gate_fails_without_token(tmp_path: Path) -> None:
    gate = UsbSecurityGate()
    with pytest.raises(PermissionError):
        gate.verify(tmp_path)


def test_usb_gate_rejects_wrong_key_id(tmp_path: Path) -> None:
    gate = UsbSecurityGate()
    gate.enroll(tmp_path)
    with pytest.raises(PermissionError):
        gate.verify(tmp_path, expected_key_id="wrong")


def test_usb_gate_does_not_treat_missing_mount_as_authorized(tmp_path: Path) -> None:
    gate = UsbSecurityGate()
    with pytest.raises(FileNotFoundError):
        gate.verify(tmp_path / "missing")
