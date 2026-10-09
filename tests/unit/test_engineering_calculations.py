import math

import pytest

from anne.engineering.calculations import (
    InputValidationError,
    preliminary_bess_screening,
    preliminary_pv_screening,
)


def test_pv_screening_does_not_invent_yield_tariff_or_capex() -> None:
    result = preliminary_pv_screening(
        roof_area_m2=100, panel_power_w=600, panel_area_m2=2.6,
        usable_roof_fraction=0.7,
    )
    assert result.status == "NEEDS_INPUT"
    assert result.values["capacity_kwp_screening"] == 16.2
    assert result.values["annual_production_kwh"] is None
    assert result.values["estimated_savings_tl"] is None
    assert "site_specific_yield_kwh_per_kwp_year" in result.missing_inputs
    assert "verified_installed_cost_tl" in result.missing_inputs


def test_pv_financial_estimates_require_explicit_inputs() -> None:
    result = preliminary_pv_screening(
        roof_area_m2=100, panel_power_w=600, panel_area_m2=2.6,
        usable_roof_fraction=0.7, specific_yield_kwh_per_kwp_year=1400,
        annual_consumption_kwh=12000, tariff_tl_per_kwh=3,
        installed_cost_tl=100000,
    )
    assert result.status == "PRELIMINARY_ESTIMATE"
    assert result.values["annual_production_kwh"] == pytest.approx(22680)
    assert result.values["estimated_self_consumption_kwh"] == 12000
    assert result.values["estimated_savings_tl"] == 36000
    assert result.values["simple_payback_years"] == pytest.approx(100000 / 36000)
    assert result.warnings


def test_pv_rejects_nonfinite_and_invalid_roof_inputs() -> None:
    with pytest.raises(InputValidationError):
        preliminary_pv_screening(
            roof_area_m2=math.inf, panel_power_w=600, panel_area_m2=2.6,
            usable_roof_fraction=0.7,
        )
    with pytest.raises(InputValidationError):
        preliminary_pv_screening(
            roof_area_m2=100, panel_power_w=600, panel_area_m2=2.6,
            usable_roof_fraction=1.2,
        )


def test_bess_runtime_and_power_constraint() -> None:
    result = preliminary_bess_screening(
        nominal_energy_kwh=20, continuous_power_kw=8, load_power_kw=5,
        depth_of_discharge=0.9, discharge_efficiency=0.92,
    )
    assert result.status == "PRELIMINARY_ESTIMATE"
    assert result.values["usable_energy_kwh_screening"] == pytest.approx(16.56)
    assert result.values["runtime_hours_at_constant_load"] == pytest.approx(3.312)
    blocked = preliminary_bess_screening(
        nominal_energy_kwh=20, continuous_power_kw=4, load_power_kw=5,
        depth_of_discharge=0.9, discharge_efficiency=0.92,
    )
    assert blocked.status == "BLOCKED"
    assert blocked.values["load_within_power_rating"] is False


@pytest.mark.parametrize("value", [math.nan, math.inf, -1, 0])
def test_bess_rejects_invalid_nominal_energy(value: float) -> None:
    with pytest.raises(InputValidationError):
        preliminary_bess_screening(
            nominal_energy_kwh=value, continuous_power_kw=8, load_power_kw=5,
            depth_of_discharge=0.9, discharge_efficiency=0.92,
        )
