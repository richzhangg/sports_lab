"""
Safe evaluation of a user-typed mathematical equation.

The student assigns single symbols to dataset columns (x = median income,
y = poverty rate, …) and writes an arbitrary formula in those symbols. The app
does NOT fit or interpret the formula — it just evaluates it for every community
and compares the result to the actual NCAA counts.

Evaluation uses numexpr, which only understands arithmetic and a fixed set of
math functions — it cannot import modules, access attributes, or call arbitrary
code, so a typed expression is safe to run.
"""
from __future__ import annotations

import re

import numpy as np
import numexpr as ne

MAX_LEN = 500
ALLOWED_FUNCS = {
    "where", "sqrt", "exp", "log", "log10", "log1p", "expm1", "abs",
    "sin", "cos", "tan", "arcsin", "arccos", "arctan", "arctan2",
    "sinh", "cosh", "tanh", "minimum", "maximum",
}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_ALLOWED_CHARS = re.compile(r"^[0-9A-Za-z_.\s+\-*/%()<>=!&|~^,]*$")


class EquationError(ValueError):
    pass


def validate(equation: str, symbols: set[str]) -> None:
    eq = (equation or "").strip()
    if not eq:
        raise EquationError("equation is empty")
    if len(eq) > MAX_LEN:
        raise EquationError(f"equation too long (max {MAX_LEN} characters)")
    if not _ALLOWED_CHARS.match(eq):
        raise EquationError("equation contains characters that are not allowed")
    names = set(_IDENT.findall(eq))
    unknown = names - symbols - ALLOWED_FUNCS - {"e", "pi"}
    if unknown:
        raise EquationError(
            f"unknown name(s): {', '.join(sorted(unknown))}. "
            f"Define them as variables, or use one of: {', '.join(sorted(ALLOWED_FUNCS))}"
        )
    if not names & symbols:
        raise EquationError("equation does not use any of the defined variables")


def evaluate(equation: str, columns: dict[str, np.ndarray]) -> np.ndarray:
    """columns: symbol -> value array (already selected for the rows to score)."""
    validate(equation, set(columns))
    local = {k: np.asarray(v, dtype="float64") for k, v in columns.items()}
    local["pi"] = np.pi
    local["e"] = np.e
    try:
        out = ne.evaluate(equation.replace("^", "**"), local_dict=local, global_dict={})
    except Exception as exc:  # noqa: BLE001
        raise EquationError(f"could not evaluate equation: {exc}")
    out = np.asarray(out, dtype="float64")
    if out.ndim == 0:
        out = np.full(len(next(iter(local.values()))), float(out))
    return out
