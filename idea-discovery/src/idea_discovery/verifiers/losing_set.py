"""Partial P-position set ("pairing / mirroring strategy") for heap games.

Certificate form (JSON):

    {"certificate_type": "losing_set",
     "member_expr": "h1 % 8 == 0 and h2 % 8 == 0 and h3 % 8 == 0"}   # truthy exactly on the claimed set L

Added after the first real-model pilot (2026-09-17): on heaps (8, 24, 2) with
moves 1..7 the model proved a first-player win by "empty the third heap, then
keep every heap a multiple of 8", never naming the nim-sum. That is a valid
idea but not a *complete* characterisation (``xor_invariant`` would reject it:
(7, 7, 0) is outside L and has no move into L), so it needs its own verifier.

The claim is that L is a set of losing positions closed under the strategy:
    * the terminal position is in L;
    * from a position in L no move stays in L;
    * from every position one move away from L (a successor of a member of L)
      some move leads back into L.
By induction the player who moves *into* L wins (the terminal position is
reached by a move into L). Exhaustive over the box containing every reachable
state; exact; never consults a theorem.

Decision relevance: start in L -> the second player wins; start has a move
into L -> the first player wins; otherwise the set says nothing about the
start (not relevant). The implied answer is compared with the ground truth.
"""
from __future__ import annotations

from ..structures import subtraction_game as sg
from ..utils.safe_expr import UnsafeExpressionError, expression_names, safe_eval
from .base import CertificateError, StepResult, Verifier, register_verifier
from .xor_invariant import MAX_EXHAUSTIVE_STATES, heap_environment


@register_verifier
class LosingSetVerifier(Verifier):
    certificate_type = "losing_set"
    method = "exhaustive"
    exact = True
    supported_structures = ("subtraction_game",)

    def normalize(self, instance, certificate: dict) -> dict:
        expr = certificate.get("member_expr") or certificate.get("losing_set_expr") or certificate.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            raise CertificateError("certificate needs 'member_expr' (true/nonzero exactly on the claimed losing set)")
        structure = instance.structure
        env = heap_environment(tuple(structure["heaps"]), structure["max_take"] or 0)
        unknown = expression_names(expr, caret="xor") - set(env)
        if unknown:
            raise CertificateError(f"member_expr uses unknown names {sorted(unknown)}; use h1..h{len(structure['heaps'])}")
        return {"certificate_type": self.certificate_type, "member_expr": expr}

    def _member(self, cert: dict, state, k: int) -> bool:
        try:
            return bool(safe_eval(cert["member_expr"], heap_environment(state, k), caret="xor"))
        except (UnsafeExpressionError, TypeError, ValueError) as e:
            raise CertificateError(f"member_expr could not be evaluated at {list(state)}: {e}") from e

    def _members(self, instance, cert: dict) -> dict:
        structure = instance.structure
        k = structure["max_take"] or 0
        return {s: self._member(cert, s, k) for s in sg.states(structure)}

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        n = sg.n_states(structure)
        if n > MAX_EXHAUSTIVE_STATES:
            return StepResult(False, f"state space {n} too large for exhaustive verification", {"n_states": n})
        try:
            members = self._members(instance, cert)
        except CertificateError as e:
            return StepResult(False, str(e), {})
        terminal = tuple(0 for _ in structure["heaps"])
        if not members[terminal]:
            return StepResult(False, "the terminal position (all heaps empty) must belong to the losing set", {"counterexample": list(terminal)})
        if all(members.values()):
            return StepResult(False, "the losing set is every position (a constant condition)", {})
        one_step_out = set()
        for s, inside in members.items():
            if not inside:
                continue
            for t in sg.moves(structure, s):
                if members[t]:
                    return StepResult(False, f"position {list(s)} is in the losing set but has a move to {list(t)}, also in the set", {"counterexample": list(s), "move_to": list(t)})
                one_step_out.add(t)
        for s in one_step_out:
            if not any(members[t] for t in sg.moves(structure, s)):
                return StepResult(False, f"position {list(s)} is reachable from the losing set in one move but has no move back into it", {"counterexample": list(s)})
        return StepResult(True, None, {"n_states": n, "set_size": sum(members.values())})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        k = structure["max_take"] or 0
        start = tuple(structure["heaps"])
        try:
            if self._member(cert, start, k):
                implied = "second"
            elif any(self._member(cert, t, k) for t in sg.moves(structure, start)):
                implied = "first"
            else:
                return StepResult(False, "the starting position is neither in the losing set nor one move away from it; the set does not decide it", {"start": list(start)})
        except CertificateError as e:
            return StepResult(False, str(e), {})
        details = {"implied_answer": implied}
        if instance.ground_truth.get("answer") != implied:
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, f"losing set implies '{implied}' but the ground truth is '{instance.ground_truth.get('answer')}'", details)
        return StepResult(True, None, details)
