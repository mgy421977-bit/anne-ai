"""General-purpose deterministic calculation engine for ANNE.

Safe arithmetic is parsed from a restricted AST. Domain formulas are registered
as deterministic functions; language models may plan and explain, never replace
the arithmetic engine.
"""
from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass
from typing import Any, Callable

from anne.engineering.calculations import (
    CalculationResult,
    InputValidationError,
    preliminary_bess_screening,
    preliminary_pv_screening,
)


class CalculationError(ValueError):
    """Invalid or unsupported deterministic calculation request."""


@dataclass(frozen=True)
class CalculationTrace:
    operation: str
    inputs: dict[str, Any]
    result: Any
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "inputs": self.inputs,
            "result": self.result,
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
        }


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def evaluate_expression(expression: str, variables: dict[str, float] | None = None) -> CalculationTrace:
    """Evaluate arithmetic only: numbers, named variables, + - * / ** %, parentheses."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("expression must be a non-empty string")
    variables = variables or {}
    checked: dict[str, float] = {}
    for name, value in variables.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise CalculationError(f"invalid variable name: {name!r}")
        number = _finite_number(name, value)
        checked[name] = number

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculationError("invalid arithmetic expression") from exc

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return _finite_number("numeric literal", node.value)
        if isinstance(node, ast.Name):
            if node.id not in checked:
                raise CalculationError(f"missing variable: {node.id}")
            return checked[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise CalculationError("exponent magnitude exceeds the safety limit of 100")
            try:
                return _finite_number("result", _BINARY[type(node.op)](left, right))
            except (ZeroDivisionError, OverflowError, ValueError) as exc:
                raise CalculationError(f"arithmetic failed: {exc}") from exc
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _finite_number("result", _UNARY[type(node.op)](visit(node.operand)))
        raise CalculationError(f"unsupported expression element: {type(node).__name__}")

    result = visit(tree)
    return CalculationTrace("arithmetic_expression", {"expression": expression, "variables": checked}, result)


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise CalculationError(f"{name} must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CalculationError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise CalculationError(f"{name} must be finite")
    return number


class DeterministicCalculationEngine:
    """Dispatch generic arithmetic and registered domain formulas."""

    def __init__(self) -> None:
        self._operations: dict[str, Callable[..., CalculationResult | CalculationTrace]] = {
            "pv_screening": preliminary_pv_screening,
            "bess_screening": preliminary_bess_screening,
        }

    @property
    def operations(self) -> tuple[str, ...]:
        return ("arithmetic_expression", *sorted(self._operations))

    def calculate(self, operation: str, **inputs: Any) -> dict[str, Any]:
        if operation == "arithmetic_expression":
            expression = inputs.pop("expression", None)
            variables = inputs.pop("variables", None)
            if inputs:
                raise CalculationError(f"unexpected inputs: {', '.join(sorted(inputs))}")
            trace = evaluate_expression(expression, variables)
            return {"ok": True, "trace": trace.to_dict()}
        formula = self._operations.get(operation)
        if formula is None:
            raise CalculationError(
                f"unknown operation {operation!r}; available operations: {', '.join(self.operations)}"
            )
        result = formula(**inputs)
        return {"ok": True, "trace": {
            "operation": result.calculation,
            "inputs": inputs,
            "result": result.to_dict(),
            "assumptions": list(result.assumptions),
            "warnings": list(result.warnings),
            "missing_inputs": list(result.missing_inputs),
            "status": result.status,
        }}


__all__ = [
    "CalculationError",
    "CalculationTrace",
    "DeterministicCalculationEngine",
    "evaluate_expression",
]
