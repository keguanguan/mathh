import math

import pytest

from idea_discovery.utils import (
    UnsafeExpressionError,
    bootstrap_mean_ci,
    canonical_json,
    derive_seed,
    expression_names,
    safe_eval,
    stable_hash,
    wilson_interval,
)


class TestSafeExpr:
    def test_arithmetic_and_mod_notation(self):
        assert safe_eval("(r + c) % 2", {"r": 3, "c": 4}) == 1
        assert safe_eval("(r + c) mod 2", {"r": 3, "c": 4}) == 1
        assert safe_eval("(r + c) modulo 2", {"r": 2, "c": 4}) == 0
        assert safe_eval("(-1)^(r+c)", {"r": 1, "c": 2}) == -1
        assert safe_eval("(-1)**(r+c)", {"r": 2, "c": 2}) == 1
        assert safe_eval("a − b", {"a": 5, "b": 2}) == 3

    def test_conditionals_and_functions(self):
        assert safe_eval("1 if r > c else 0", {"r": 3, "c": 1}) == 1
        assert safe_eval("abs(a - b) + max(a, b)", {"a": 1, "b": 4}) == 7
        assert safe_eval("r == c", {"r": 1, "c": 1}) == 1

    def test_rejects_unsafe(self):
        with pytest.raises(UnsafeExpressionError):
            safe_eval("__import__('os').system('x')", {})
        with pytest.raises(UnsafeExpressionError):
            safe_eval("r.real", {"r": 1})
        with pytest.raises(UnsafeExpressionError):
            safe_eval("unknown + 1", {"r": 1})
        with pytest.raises(UnsafeExpressionError):
            safe_eval("2 ** 100000", {})
        with pytest.raises(UnsafeExpressionError):
            safe_eval("1 / 0", {})
        with pytest.raises(UnsafeExpressionError):
            safe_eval("(r + ", {"r": 1})

    def test_expression_names(self):
        assert expression_names("(r + c) % 2 + abs(x)") == {"r", "c", "x"}


class TestHashing:
    def test_deterministic(self):
        assert stable_hash({"a": 1, "b": [1, 2]}) == stable_hash({"b": [1, 2], "a": 1})
        assert derive_seed("family", 8, 1) == derive_seed("family", 8, 1)
        assert derive_seed("family", 8, 1) != derive_seed("family", 8, 2)

    def test_canonical_json_handles_tuples_and_sets(self):
        assert canonical_json({"x": (1, 2), "s": {2, 1}}) == '{"s":[1,2],"x":[1,2]}'


class TestStats:
    def test_wilson(self):
        lo, hi = wilson_interval(5, 10)
        assert 0.2 < lo < 0.5 < hi < 0.8
        assert wilson_interval(0, 10)[0] == 0.0
        assert wilson_interval(10, 10)[1] == pytest.approx(1.0)
        assert all(math.isnan(v) for v in wilson_interval(0, 0))

    def test_bootstrap(self):
        lo, hi = bootstrap_mean_ci([0, 1] * 50, n_boot=200, seed=1)
        assert lo < 0.5 < hi
