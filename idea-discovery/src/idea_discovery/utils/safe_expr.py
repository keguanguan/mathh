"""Safe evaluation of small arithmetic expressions supplied by models.

Certificates may contain formulas such as ``"(r + c) % 2"`` or
``"(a - b) mod 3"``. These are evaluated with a whitelisted AST walker,
never with ``eval``.
"""
from __future__ import annotations

import ast
import operator
import re
from typing import Any, Mapping

__all__ = ["UnsafeExpressionError", "normalize_expression", "safe_eval", "expression_names"]


class UnsafeExpressionError(ValueError):
    """Raised when an expression uses disallowed syntax or unknown names."""


_BINOPS = {
    ast.BitXor: operator.xor,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Div: operator.truediv,
    ast.Pow: None,  # handled specially (exponent bound)
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}
_COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


def _xor(*args):
    out = 0
    for a in args:
        out ^= int(a)
    return out


_FUNCS = {"abs": abs, "min": min, "max": max, "int": int, "xor": _xor, "nimsum": _xor}
_MAX_EXPONENT = 64


def normalize_expression(expr: str, caret: str = "power") -> str:
    """Map common mathematical notation onto Python syntax.

    ``caret="power"`` reads ``^`` as exponentiation (the usual mathematical
    reading); ``caret="xor"`` keeps it as bitwise XOR (game-theory certificates).
    """
    s = expr.strip()
    s = s.replace("\u2212", "-").replace("\u2013", "-").replace("\u00d7", "*").replace("\u00b7", "*")
    s = s.replace("\u2295", "^")  # circled plus is XOR
    if caret == "power":
        s = s.replace("^", "**")
    s = re.sub(r"\bmodulo\b", "%", s)
    s = re.sub(r"\bmod\b", "%", s)
    return s


def expression_names(expr: str, caret: str = "power") -> set[str]:
    """Variable names referenced by an expression (after normalization)."""
    try:
        tree = ast.parse(normalize_expression(expr, caret), mode="eval")
    except SyntaxError as e:
        raise UnsafeExpressionError(f"syntax error: {e}") from e
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id not in _FUNCS}


def safe_eval(expr: str, variables: Mapping[str, Any], caret: str = "power") -> Any:
    """Evaluate ``expr`` with the given variable bindings.

    Only integer/float literals, arithmetic, bitwise xor/and/or, comparisons,
    boolean operations, conditional expressions and the functions
    abs/min/max/int/xor are permitted.
    """
    try:
        tree = ast.parse(normalize_expression(expr, caret), mode="eval")
    except SyntaxError as e:
        raise UnsafeExpressionError(f"syntax error in expression {expr!r}: {e.msg}") from e
    value = _eval_node(tree.body, variables)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _eval_node(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (bool, int, float)):
            return node.value
        raise UnsafeExpressionError(f"literal {node.value!r} not allowed")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise UnsafeExpressionError(f"unknown variable {node.id!r}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise UnsafeExpressionError(f"operator {op_type.__name__} not allowed")
        left = _eval_node(node.left, env)
        right = _eval_node(node.right, env)
        if op_type is ast.Pow:
            if not isinstance(right, int) or abs(right) > _MAX_EXPONENT:
                raise UnsafeExpressionError("exponent must be an integer with |e| <= 64")
            return left**right
        try:
            return _BINOPS[op_type](left, right)
        except ZeroDivisionError as e:
            raise UnsafeExpressionError("division by zero") from e
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY:
            raise UnsafeExpressionError(f"unary operator {op_type.__name__} not allowed")
        return _UNARY[op_type](_eval_node(node.operand, env))
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise UnsafeExpressionError("boolean operator not allowed")
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env)
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in _COMPARE:
                raise UnsafeExpressionError(f"comparison {op_type.__name__} not allowed")
            right = _eval_node(comparator, env)
            if not _COMPARE[op_type](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        cond = _eval_node(node.test, env)
        return _eval_node(node.body, env) if cond else _eval_node(node.orelse, env)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS or node.keywords:
            raise UnsafeExpressionError("only abs/min/max/int calls are allowed")
        args = [_eval_node(a, env) for a in node.args]
        return _FUNCS[node.func.id](*args)
    raise UnsafeExpressionError(f"syntax {type(node).__name__} not allowed")
