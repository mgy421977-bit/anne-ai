"""Deterministic, assumption-explicit preliminary engineering calculations.

This module is an ANNE-owned calculation layer for early screening. It is not a
bankable yield model, construction design, or substitute for qualified engineering
review. Missing inputs are reported rather than silently invented.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


class InputValidationError(ValueError):
    """Raised when a supplied numeric input is invalid."""


def _positive(name: str, value: float, *, allow_zero: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise InputValidationError(f"{name} must be finite")
    if number < 0 or (number == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise InputValidationError(f"{name} must be {qualifier}")
    return number


@dataclass(frozen=True)
class CalculationResult:
    calculation: str
    status: str
    values: dict[str, Any]
    assumptions: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def preliminary_pv_screening(
    *,
    roof_area_m2: float,
    panel_power_w: float,
    panel_area_m2: float,
    usable_roof_fraction: float,
    specific_yield_kwh_per_kwp_year: float | None = None,
    annual_consumption_kwh: float | None = None,
    tariff_tl_per_kwh: float | None = None,
    installed_cost_tl: float | None = None,
) -> CalculationResult:
    """Estimate geometric PV capacity; financial values require explicit inputs."""
    roof = _positive("roof_area_m2", roof_area_m2)
    panel_w = _positive("panel_power_w", panel_power_w)
    panel_area = _positive("panel_area_m2", panel_area_m2)
    usable = float(usable_roof_fraction)
    if not math.isfinite(usable) or not 0 < usable <= 1:
        raise InputValidationError("usable_roof_fraction must be in (0, 1]")

    usable_area = roof * usable
    panel_count = math.floor(usable_area / panel_area)
    capacity_kwp = panel_count * panel_w / 1000
    values: dict[str, Any] = {
        "roof_area_m2": roof,
        "usable_roof_area_m2": usable_area,
        "panel_count_screening": panel_count,
        "capacity_kwp_screening": capacity_kwp,
        "annual_production_kwh": None,
        "annual_consumption_kwh": None,
        "estimated_self_consumption_kwh": None,
        "estimated_savings_tl": None,
        "simple_payback_years": None,
    }
    missing: list[str] = []
    assumptions = ["Geometric roof screening only; no shading, setbacks, structure, string, inverter, grid or weather simulation."]
    warnings: list[str] = []

    if specific_yield_kwh_per_kwp_year is None:
        missing.append("site_specific_yield_kwh_per_kwp_year")
    else:
        yield_value = _positive("specific_yield_kwh_per_kwp_year",
                                specific_yield_kwh_per_kwp_year)
        values["annual_production_kwh"] = capacity_kwp * yield_value
        assumptions.append("Specific yield supplied by caller; not independently verified.")

    if annual_consumption_kwh is None:
        missing.append("annual_consumption_kwh")
    else:
        consumption = _positive("annual_consumption_kwh", annual_consumption_kwh)
        values["annual_consumption_kwh"] = consumption
        production = values["annual_production_kwh"]
        if production is not None:
            # This is only an energy ceiling, not a time-resolved self-consumption model.
            values["estimated_self_consumption_kwh"] = min(production, consumption)
            warnings.append("Self-consumption is an annual-energy upper bound, not an hourly dispatch result.")

    if tariff_tl_per_kwh is None:
        missing.append("applicable_tariff_tl_per_kwh")
    else:
        tariff = _positive("tariff_tl_per_kwh", tariff_tl_per_kwh, allow_zero=True)
        self_consumption = values["estimated_self_consumption_kwh"]
        if self_consumption is not None:
            values["estimated_savings_tl"] = self_consumption * tariff
            warnings.append("Savings exclude tariff structure, taxes, export compensation, degradation, O&M and timing effects.")

    if installed_cost_tl is None:
        missing.append("verified_installed_cost_tl")
    else:
        cost = _positive("installed_cost_tl", installed_cost_tl, allow_zero=True)
        savings = values["estimated_savings_tl"]
        if savings is not None and savings > 0 and cost > 0:
            values["simple_payback_years"] = cost / savings
            warnings.append("Simple undiscounted payback only; financing, O&M, degradation, replacements, tax and discounting excluded.")
        elif cost > 0 and savings == 0:
            warnings.append("Payback not calculated because estimated savings are zero.")

    if panel_count == 0:
        warnings.append("Usable roof area does not fit one panel under the supplied dimensions.")
    return CalculationResult(
        calculation="preliminary_pv_screening",
        status="NEEDS_INPUT" if missing else "PRELIMINARY_ESTIMATE",
        values=values,
        assumptions=tuple(assumptions),
        missing_inputs=tuple(missing),
        warnings=tuple(warnings),
    )


def preliminary_bess_screening(
    *,
    nominal_energy_kwh: float,
    continuous_power_kw: float,
    load_power_kw: float,
    depth_of_discharge: float,
    discharge_efficiency: float,
) -> CalculationResult:
    """Estimate usable battery energy and runtime at a constant load."""
    energy = _positive("nominal_energy_kwh", nominal_energy_kwh)
    power = _positive("continuous_power_kw", continuous_power_kw)
    load = _positive("load_power_kw", load_power_kw)
    dod = float(depth_of_discharge)
    efficiency = float(discharge_efficiency)
    if not math.isfinite(dod) or not 0 < dod <= 1:
        raise InputValidationError("depth_of_discharge must be in (0, 1]")
    if not math.isfinite(efficiency) or not 0 < efficiency <= 1:
        raise InputValidationError("discharge_efficiency must be in (0, 1]")

    usable = energy * dod * efficiency
    warnings: list[str] = []
    if load > power:
        warnings.append("Requested load exceeds the supplied continuous power rating.")
    if usable / energy > 0.95:
        warnings.append("Check that depth of discharge and efficiency match the selected battery datasheet.")
    return CalculationResult(
        calculation="preliminary_bess_screening",
        status="PRELIMINARY_ESTIMATE" if load <= power else "BLOCKED",
        values={
            "nominal_energy_kwh": energy,
            "usable_energy_kwh_screening": usable,
            "continuous_power_kw": power,
            "load_power_kw": load,
            "runtime_hours_at_constant_load": usable / load,
            "load_within_power_rating": load <= power,
        },
        assumptions=(
            "Constant load and simplified usable-energy calculation.",
            "No temperature, aging, auxiliary loads, inverter overload, reserve, control strategy or battery datasheet model.",
        ),
        warnings=tuple(warnings),
    )
