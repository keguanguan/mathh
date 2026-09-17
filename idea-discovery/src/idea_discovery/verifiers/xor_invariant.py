"""P-position characterisation (XOR / nim-sum type) for heap games.

Certificate form (JSON):

    {"certificate_type": "xor_invariant",
     "losing_expr": "xor(h1 % 4, h2 % 4, h3 % 4)"}     # == 0 exactly at losing positions

Variables: h1..hk (also a, b, c, ...; ``heaps`` is not available - name the
heaps). ``^`` is XOR here; ``xor(...)``/``nimsum(...)`` are also accepted.

The claim is that the positions where the expression is 0 are exactly the
P-positions (the player to move loses). Structural check, exhaustive over the
box prod(h_i + 1) that contains every reachable state:
    * the terminal position has value 0;
    * from a 0-position every move leads to a non-0 position;
    * from a non-0 position some move leads to a 0-position.
Method is "exhaustive" and exact; it never consults the theorem. A constant
expression fails at the first non-terminal position.

Decision relevance: a correct characterisation decides every position, so
the certificate is relevant whenever it is structurally valid; the answer it
yields is recorded and compared with the instance ground truth.
"""
from __future__ import annotations

from ..structures import subtraction_game as sg
from ..utils.safe_expr import UnsafeExpressionError, expression_names, safe_eval
from .base import CertificateError, StepResult, Verifier, register_verifier

MAX_EXHAUSTIVE_STATES = 1_500_000


def heap_environment(state, k: int) -> dict[str, int]:
    env = {f"h{i + 1}": v for i, v in enumerate(state)}
    for i, v in enumerate(state):
        env[f"x{i + 1}"] = v
        env["abcdefghijklmnopqrstuvwxyz"[i]] = v
    env["k"] = k
    return env


@register_verifier
class XorInvariantVerifier(Verifier):
    certificate_type = "xor_invariant"
    method = "exhaustive"
    exact = True
    supported_structures = ("subtraction_game",)

    def normalize(self, instance, certificate: dict) -> dict:
        expr = certificate.get("losing_expr") or certificate.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            raise CertificateError("certificate needs 'losing_expr' (an expression that is 0 exactly at losing positions)")
        structure = instance.structure
        env = heap_environment(tuple(structure["heaps"]), structure["max_take"] or 0)
        unknown = expression_names(expr, caret="xor") - set(env)
        if unknown:
            raise CertificateError(f"losing_expr uses unknown names {sorted(unknown)}; use h1..h{len(structure['heaps'])}")
        return {"certificate_type": self.certificate_type, "losing_expr": expr}

    def _value(self, cert: dict, state, k: int) -> int:
        try:
            return int(safe_eval(cert["losing_expr"], heap_environment(state, k), caret="xor"))
        except (UnsafeExpressionError, TypeError, ValueError) as e:
            raise CertificateError(f"losing_expr could not be evaluated at {list(state)}: {e}") from e

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        n = sg.n_states(structure)
        if n > MAX_EXHAUSTIVE_STATES:
            return StepResult(False, f"state space {n} too large for exhaustive verification", {"n_states": n})
        k = structure["max_take"] or 0
        try:
            values = {s: self._value(cert, s, k) == 0 for s in sg.states(structure)}
        except CertificateError as e:
            return StepResult(False, str(e), {})
        terminal = tuple(0 for _ in structure["heaps"])
        if not values[terminal]:
            return StepResult(False, "terminal position (all heaps empty) must be a losing position but the expression is non-zero there", {"counterexample": list(terminal)})
        for s, losing in values.items():
            succ = list(sg.moves(structure, s))
            if losing:
                bad = [t for t in succ if values[t]]
                if bad:
                    return StepResult(False, f"position {list(s)} is claimed losing but has a move to the claimed-losing position {list(bad[0])}", {"counterexample": list(s), "move_to": list(bad[0])})
            else:
                if not any(values[t] for t in succ):
                    return StepResult(False, f"position {list(s)} is claimed winning but no move reaches a claimed-losing position", {"counterexample": list(s)})
        return StepResult(True, None, {"n_states": n})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        k = structure["max_take"] or 0
        try:
            v = self._value(cert, tuple(structure["heaps"]), k)
        except CertificateError as e:
            return StepResult(False, str(e), {})
        implied = "second" if v == 0 else "first"
        details = {"value_at_start": v, "implied_answer": implied}
        if instance.ground_truth.get("answer") != implied:
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, f"characterisation implies '{implied}' but the ground truth is '{instance.ground_truth.get('answer')}'", details)
        return StepResult(True, None, details)
