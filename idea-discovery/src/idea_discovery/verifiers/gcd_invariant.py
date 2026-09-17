"""Divisibility (gcd) invariant for difference-board structures.

Certificate form (JSON):

    {"certificate_type": "gcd_invariant", "divisor": 6}

Claim: every number that can ever be written is a multiple of ``divisor``.
Structural check (exact): the divisor divides every initial number, and the
board operation maps multiples of the divisor to multiples of the divisor
(checked on residue classes). Decision relevance: the target is *not* a
multiple of the divisor. ``divisor = 1`` is structurally valid but useless.
Any divisor of gcd(numbers) that does not divide the target is a valid
non-canonical certificate.
"""
from __future__ import annotations

from ..structures import difference_board as db
from .base import CertificateError, StepResult, Verifier, register_verifier
from .coloring_invariant import _as_int


@register_verifier
class GcdInvariantVerifier(Verifier):
    certificate_type = "gcd_invariant"
    method = "symbolic"
    exact = True
    supported_structures = ("difference_board",)

    def normalize(self, instance, certificate: dict) -> dict:
        d = certificate.get("divisor", certificate.get("modulus"))
        if d is None:
            raise CertificateError("certificate needs 'divisor'")
        d = _as_int(d, "divisor")
        if d < 1:
            raise CertificateError("divisor must be a positive integer")
        return {"certificate_type": self.certificate_type, "divisor": d}

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        d = cert["divisor"]
        bad = [x for x in structure["numbers"] if x % d != 0]
        if bad:
            return StepResult(False, f"initial number {bad[0]} is not a multiple of {d}", {"counterexample": bad[0]})
        if not db.preserves_divisibility(structure["operation"], d):
            return StepResult(False, f"the operation {structure['operation']} does not preserve divisibility by {d}", {})
        return StepResult(True, None, {"divisor": d, "n_initial_checked": len(structure["numbers"])})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        d = cert["divisor"]
        t = instance.structure["target"]
        details = {"divisor": d, "target": t, "target_residue": t % d}
        if d == 1:
            return StepResult(False, "divisor 1: every integer is a multiple, the invariant separates nothing", details)
        if t % d == 0:
            if instance.ground_truth.get("answer") == "possible":
                return StepResult(False, "target is a multiple of the divisor; the invariant cannot certify possibility", details)
            return StepResult(False, "target is a multiple of the divisor; the invariant does not exclude it", details)
        if instance.ground_truth.get("answer") == "possible":
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, "invariant claims impossibility but the instance ground truth is 'possible'", details)
        return StepResult(True, None, details)
