from anne.core.resource_profile import ResourceProfile
from anne.core.windows_execution import WindowsExecutionAdapter


def test_non_windows_plan_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.windows_execution.platform.system", lambda: "Linux")
    plan = WindowsExecutionAdapter.plan(ResourceProfile.minimal())
    assert plan.status == "UNAVAILABLE"
    assert plan.requires_authorization is True


def test_windows_plan_is_side_effect_free(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.windows_execution.platform.system", lambda: "Windows")
    plan = WindowsExecutionAdapter.plan(
        ResourceProfile.scaled(capacity=2),
        background=True,
        cpu_mask=0x3,
    )
    assert plan.status == "READY"
    assert plan.priority == "below_normal"
    assert plan.affinity_mask == 0x3


def test_apply_requires_explicit_authorization(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.windows_execution.platform.system", lambda: "Windows")
    plan = WindowsExecutionAdapter.plan(ResourceProfile.minimal())
    result = WindowsExecutionAdapter().apply(plan, authorized=False)
    assert result.status == "DENIED"
    assert result.applied == ()
    assert "windows_controls" in result.skipped


def test_capabilities_are_false_off_windows(monkeypatch) -> None:
    monkeypatch.setattr("anne.core.windows_execution.platform.system", lambda: "Linux")
    capabilities = WindowsExecutionAdapter().capabilities()
    assert capabilities.windows is False
    assert capabilities.any_control is False
