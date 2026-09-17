"""Permutation-parity invariant for sliding-puzzle structures.

Certificate forms (JSON):

    {"certificate_type": "permutation_parity",
     "permutation_of": "all_cells" | "tiles_only",
     "blank_term": "taxicab" | "row" | "col" | "none"}          # grid surfaces

    {"certificate_type": "permutation_parity",
     "permutation_of": "all_cells",
     "blank_expr": "(r + c) % 2"}                               # any 0/1 expression in r, c

    {"certificate_type": "permutation_parity",
     "permutation_of": "all_cells",
     "blank_weights": {"<vertex label>": 0 or 1, ...}}          # graph surfaces

The claimed invariant is phi = (inversion parity of the chosen sequence +
blank weight) mod 2. Structural check (local rule, O(#edges)): for every edge
(u, v) the move along it changes phi by delta_perm(u, v) + w(u) + w(v) == 0
(mod 2). Decision relevance: phi(start) != phi(target).
"""
from __future__ import annotations

from ..structures import sliding_puzzle as sp
from ..utils.safe_expr import UnsafeExpressionError, safe_eval
from .base import CertificateError, StepResult, Verifier, register_verifier
from .coloring_invariant import _as_int, label_to_cell_map, parse_cell

BLANK_TERMS = {"taxicab": lambda r, c: (r + c) % 2, "row": lambda r, c: r % 2, "col": lambda r, c: c % 2, "none": lambda r, c: 0}
PERMUTATION_OF = ("all_cells", "tiles_only")


@register_verifier
class PermutationParityVerifier(Verifier):
    certificate_type = "permutation_parity"
    method = "local_rule"
    exact = True
    supported_structures = ("sliding_puzzle",)

    def normalize(self, instance, certificate: dict) -> dict:
        structure = instance.structure
        perm_of = certificate.get("permutation_of", "all_cells")
        if perm_of not in PERMUTATION_OF:
            raise CertificateError(f"permutation_of must be one of {PERMUTATION_OF}")
        weight: dict[tuple[int, int], int] = {}
        if certificate.get("blank_weights") is not None:
            raw = certificate["blank_weights"]
            if not isinstance(raw, dict):
                raise CertificateError("blank_weights must be an object")
            label_map = label_to_cell_map(instance)
            for key, value in raw.items():
                weight[parse_cell(key, label_map)] = _as_int(value, f"weight of {key!r}") % 2
            missing = [cell for cell in sp.cells(structure) if cell not in weight]
            if missing:
                raise CertificateError(f"blank_weights missing for {len(missing)} cells, e.g. {missing[:3]}")
            source = "blank_weights"
        elif certificate.get("blank_expr") is not None:
            expr = certificate["blank_expr"]
            if not isinstance(expr, str) or not expr.strip():
                raise CertificateError("blank_expr must be a non-empty string")
            for r, c in sp.cells(structure):
                try:
                    value = safe_eval(expr, {"r": r, "c": c, "row": r, "col": c, "i": r, "j": c, "R": structure["rows"], "C": structure["cols"]})
                except UnsafeExpressionError as e:
                    raise CertificateError(f"blank_expr could not be evaluated: {e}") from e
                weight[(r, c)] = _as_int(value, "blank_expr value") % 2
            source = f"blank_expr: {expr}"
        else:
            term = certificate.get("blank_term", "none")
            if term not in BLANK_TERMS:
                raise CertificateError(f"blank_term must be one of {sorted(BLANK_TERMS)}")
            weight = {(r, c): BLANK_TERMS[term](r, c) for r, c in sp.cells(structure)}
            source = f"blank_term: {term}"
        return {
            "certificate_type": self.certificate_type,
            "permutation_of": perm_of,
            "blank_weight": {f"{r},{c}": w for (r, c), w in sorted(weight.items())},
            "source": source,
        }

    @staticmethod
    def _weight(cert: dict) -> dict[tuple[int, int], int]:
        return {tuple(int(x) for x in k.split(",")): v for k, v in cert["blank_weight"].items()}

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        w = self._weight(cert)
        for u, v in sp.edges(structure):
            delta = (sp.delta_perm(structure, u, v, cert["permutation_of"]) + w[u] + w[v]) % 2
            if delta != 0:
                return StepResult(False, f"a move along the edge {u}-{v} changes the claimed invariant", {"counterexample_edge": [list(u), list(v)]})
        return StepResult(True, None, {"n_edges_checked": len(sp.edges(structure))})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        w = self._weight(cert)
        phi_s = sp.parity_invariant(structure, sp.to_grid(structure["start"]), cert["permutation_of"], w)
        phi_t = sp.parity_invariant(structure, sp.to_grid(structure["target"]), cert["permutation_of"], w)
        details = {"phi_start": phi_s, "phi_target": phi_t}
        if phi_s == phi_t:
            if instance.ground_truth.get("answer") == "possible":
                return StepResult(False, "invariant agrees on start and target; it cannot certify possibility", details)
            return StepResult(False, "invariant takes the same value on start and target", details)
        if instance.ground_truth.get("answer") == "possible":
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, "invariant claims impossibility but the instance ground truth is 'possible'", details)
        return StepResult(True, None, details)
