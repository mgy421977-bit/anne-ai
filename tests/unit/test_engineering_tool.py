from anne.agent.runtime import AnneAgent
from anne.safety.policy import ToolPolicy


def test_engineering_calculation_tool_uses_deterministic_pv_formula() -> None:
    result = AnneAgent._engineering_calculate(
        calculation="pv",
        roof_area_m2=100,
        panel_power_w=600,
        panel_area_m2=2.6,
        usable_roof_fraction=0.7,
        specific_yield_kwh_per_kwp_year=1400,
    )
    assert result["ok"] is True
    values = result["result"]["values"]
    assert values["panel_count_screening"] == 26
    assert values["capacity_kwp_screening"] == 15.6
    assert values["annual_production_kwh"] == 21840


def test_engineering_calculation_tool_does_not_invent_missing_inputs() -> None:
    result = AnneAgent._engineering_calculate(
        calculation="pv",
        roof_area_m2=100,
        panel_power_w=600,
        panel_area_m2=2.6,
        usable_roof_fraction=0.7,
    )
    assert result["ok"] is True
    payload = result["result"]
    assert payload["values"]["annual_production_kwh"] is None
    assert "site_specific_yield_kwh_per_kwp_year" in payload["missing_inputs"]


def test_engineering_calculation_tool_rejects_invalid_inputs() -> None:
    result = AnneAgent._engineering_calculate(
        calculation="pv",
        roof_area_m2=-1,
        panel_power_w=600,
        panel_area_m2=2.6,
        usable_roof_fraction=0.7,
    )
    assert result["ok"] is False
    assert "roof_area_m2" in result["error"]


def test_engineering_calculation_is_allowlisted() -> None:
    decision = ToolPolicy().authorize("engineering_calculate", {"calculation": "pv"})
    assert decision.allowed is True
    assert decision.side_effect is False
