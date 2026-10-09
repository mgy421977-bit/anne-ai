import pytest

from anne.calculation.engine import (
    CalculationError,
    DeterministicCalculationEngine,
    evaluate_expression,
)
from anne.safety.policy import ToolPolicy


def test_general_arithmetic_is_deterministic_and_traceable() -> None:
    first = evaluate_expression("(a + b) * 3 / 2", {"a": 4, "b": 6})
    second = evaluate_expression("(a + b) * 3 / 2", {"a": 4, "b": 6})
    assert first.result == 15
    assert first.to_dict() == second.to_dict()
    assert first.inputs["variables"] == {"a": 4.0, "b": 6.0}


def test_arithmetic_rejects_code_execution_and_unknown_names() -> None:
    with pytest.raises(CalculationError):
        evaluate_expression("__import__('os').system('echo unsafe')")
    with pytest.raises(CalculationError, match="missing variable"):
        evaluate_expression("roof * 2", {})


def test_arithmetic_rejects_division_by_zero_and_nonfinite_results() -> None:
    with pytest.raises(CalculationError):
        evaluate_expression("1 / 0")
    with pytest.raises(CalculationError):
        evaluate_expression("10 ** 1000")


def test_domain_formula_registry_keeps_pv_as_a_module() -> None:
    engine = DeterministicCalculationEngine()
    result = engine.calculate(
        "pv_screening",
        roof_area_m2=100,
        panel_power_w=600,
        panel_area_m2=2.6,
        usable_roof_fraction=0.7,
        specific_yield_kwh_per_kwp_year=1400,
    )
    assert result["ok"] is True
    assert result["trace"]["result"]["values"]["capacity_kwp_screening"] == 15.6
    assert "bess_screening" in engine.operations


def test_general_calculation_tool_is_allowlisted() -> None:
    assert ToolPolicy().authorize(
        "deterministic_calculate", {"operation": "arithmetic_expression"}
    ).allowed is True
