"""Modular (linear) invariant for vector-game structures.

Certificate forms (JSON):

    {"certificate_type": "modular_invariant",
     "coefficients": [1, -1, 0],      # or {"A": 1, "B": -1}
     "modulus": 3}

    {"certificate_type": "modular_invariant",
     "expr": "(A - B) % 3"}            # arbitrary expression in the class counts

Linear certificates are verified against the *move rule* only: alpha . v == 0
(mod m) for every move v. That is exact and independent of the population
size. Expression certificates are verified exhaustively over all states with
the conserved total when that space is small, and by sampling otherwise
(recorded as method="sampled", exact=False).

Decision relevance: phi(initial) differs from phi(t) for every target t.
"""
from __future__ import annotations

import random
from typing import Any

from ..structures import vector_game as vg
from ..utils.safe_expr import UnsafeExpressionError, expression_names, safe_eval
from .base import CertificateError, StepResult, Verifier, register_verifier

MAX_EXHAUSTIVE_STATES = 200_000
N_SAMPLED_STATES = 5_000


def _as_int(value: Any, what: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            pass
    raise CertificateError(f"{what} must be an integer, got {value!r}")


def class_aliases(instance) -> list[list[str]]:
    """Per-class name aliases: structure class names plus any surface display names."""
    structure = instance.structure
    aliases = [[str(name)] for name in structure["classes"]]
    surface_names = (instance.surface or {}).get("class_names")
    if surface_names:
        for i, name in enumerate(surface_names[: len(aliases)]):
            aliases[i].append(str(name))
    return aliases


def class_environment(structure: dict, state, aliases: list[list[str]] | None = None) -> dict[str, int]:
    """Variable bindings for expression certificates: class names (exact and
    lower-case, incl. surface display names), x1..xk / n1..nk, and positional
    letters a, b, c, ... when they do not collide with class names."""
    aliases = aliases or [[str(name)] for name in structure["classes"]]
    env: dict[str, int] = {}
    for i, (names, value) in enumerate(zip(aliases, state)):
        for name in names:
            env[name] = value
            env[name.lower()] = value
            env[f"N_{name}"] = value
            env[f"n_{name}"] = value
        env[f"x{i + 1}"] = value
        env[f"n{i + 1}"] = value
    for i, value in enumerate(state):
        letter = "abcdefghijklmnopqrstuvwxyz"[i]
        env.setdefault(letter, value)
    return env


@register_verifier
class ModularInvariantVerifier(Verifier):
    certificate_type = "modular_invariant"
    method = "local_rule"
    exact = True
    supported_structures = ("vector_game",)

    def normalize(self, instance, certificate: dict) -> dict:
        structure = instance.structure
        classes = [str(c) for c in structure["classes"]]
        k = len(classes)
        if certificate.get("expr") is not None:
            expr = certificate["expr"]
            if not isinstance(expr, str) or not expr.strip():
                raise CertificateError("expr must be a non-empty string")
            env = class_environment(structure, structure["initial"], class_aliases(instance))
            unknown = expression_names(expr) - set(env)
            if unknown:
                raise CertificateError(f"expr uses unknown names {sorted(unknown)}; class names are {classes}")
            modulus = certificate.get("modulus")
            modulus = _as_int(modulus, "modulus") if modulus is not None else None
            return {"certificate_type": self.certificate_type, "form": "expr", "expr": expr, "modulus": modulus, "aliases": class_aliases(instance)}
        if certificate.get("coefficients") is None:
            raise CertificateError("certificate needs 'coefficients' (with 'modulus') or 'expr'")
        raw = certificate["coefficients"]
        if isinstance(raw, dict):
            lowered = {alias.lower(): i for i, names in enumerate(class_aliases(instance)) for alias in names}
            coefficients = [0] * k
            for name, value in raw.items():
                key = str(name).lower()
                if key not in lowered:
                    raise CertificateError(f"unknown class {name!r}; classes are {classes}")
                coefficients[lowered[key]] = _as_int(value, f"coefficient of {name}")
        elif isinstance(raw, (list, tuple)):
            if len(raw) != k:
                raise CertificateError(f"expected {k} coefficients, got {len(raw)}")
            coefficients = [_as_int(v, "coefficient") for v in raw]
        else:
            raise CertificateError("coefficients must be a list or an object keyed by class name")
        if certificate.get("modulus") is None:
            raise CertificateError("linear certificate needs a 'modulus'")
        modulus = _as_int(certificate["modulus"], "modulus")
        if modulus < 1:
            raise CertificateError("modulus must be >= 1")
        return {
            "certificate_type": self.certificate_type,
            "form": "linear",
            "coefficients": [c % modulus for c in coefficients],
            "modulus": modulus,
        }

    # -- evaluation helpers ---------------------------------------------
    def _phi(self, structure: dict, cert: dict, state) -> Any:
        if cert["form"] == "linear":
            return vg.linear_form(cert["coefficients"], state, cert["modulus"])
        env = class_environment(structure, state, cert.get("aliases"))
        try:
            value = safe_eval(cert["expr"], env)
        except UnsafeExpressionError as e:
            raise CertificateError(f"expr could not be evaluated at state {list(state)}: {e}") from e
        if cert["modulus"]:
            value = value % cert["modulus"]
        return value

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        moves = structure["moves"]
        if cert["form"] == "linear":
            for idx, move in enumerate(moves):
                value = vg.linear_form(cert["coefficients"], move, cert["modulus"])
                if value != 0:
                    return StepResult(False, f"move {idx + 1} {move} changes the form by {value} (mod {cert['modulus']})", {"counterexample_move": idx + 1, "change": value})
            return StepResult(True, None, {"n_moves_checked": len(moves)}, method="local_rule", exact=True)
        # expression form: exhaustive over the conserved-total state space, else sampled
        k = vg.dimension(structure)
        n = vg.total(structure)
        if not vg.is_conservative(structure):
            return StepResult(False, "expression invariants are only verified for conservative games", {})
        n_states = vg.count_states(k, n)
        if n_states <= MAX_EXHAUSTIVE_STATES:
            states = vg.enumerate_states(k, n)
            method, exact = "exhaustive", True
        else:
            rng = random.Random(0)
            states = (_random_composition(rng, k, n) for _ in range(N_SAMPLED_STATES))
            method, exact = "sampled", False
        checked = 0
        try:
            for state in states:
                base = self._phi(structure, cert, state)
                for idx, move in enumerate(moves):
                    nxt = vg.apply_move(state, move)
                    if nxt is None:
                        continue
                    checked += 1
                    if self._phi(structure, cert, nxt) != base:
                        return StepResult(False, f"move {idx + 1} applied at state {list(state)} changes the expression", {"counterexample_state": list(state), "counterexample_move": idx + 1}, method=method, exact=exact)
        except CertificateError as e:
            return StepResult(False, str(e), {}, method=method, exact=exact)
        return StepResult(True, None, {"n_transitions_checked": checked, "n_states": n_states}, method=method, exact=exact)

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        try:
            phi_init = self._phi(structure, cert, structure["initial"])
            phi_targets = [self._phi(structure, cert, t) for t in structure["targets"]]
        except CertificateError as e:
            return StepResult(False, str(e), {})
        details = {"phi_initial": phi_init, "phi_targets": phi_targets}
        if cert["form"] == "linear" and (cert["modulus"] == 1 or all(c == 0 for c in cert["coefficients"])):
            return StepResult(False, "constant invariant (zero form or modulus 1): it cannot separate any two states", details)
        colliding = [t for t, p in zip(structure["targets"], phi_targets) if p == phi_init]
        if colliding:
            details["colliding_targets"] = colliding
            return StepResult(False, f"invariant takes the same value on the initial state and on target {colliding[0]}", details)
        if instance.ground_truth.get("answer") == "possible":
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, "invariant claims impossibility but the instance ground truth is 'possible'", details)
        return StepResult(True, None, details)


def _random_composition(rng: random.Random, k: int, n: int) -> tuple[int, ...]:
    cuts = sorted(rng.randint(0, n) for _ in range(k - 1))
    parts = []
    prev = 0
    for c in cuts:
        parts.append(c - prev)
        prev = c
    parts.append(n - prev)
    return tuple(parts)
