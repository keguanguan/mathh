"""Coloring / weighting invariant for tiling structures.

Certificate forms (JSON):

    {"certificate_type": "coloring_invariant",
     "weight_expr": "(r + c) % 2",        # weight of cell (r, c), 1-based
     "modulus": null}                      # optional: compare tile sums mod m

    {"certificate_type": "coloring_invariant",
     "weights": {"<cell or vertex label>": <int>, ...}}   # explicit table

Structural validity: every legal placement of every tile shape has the same
total weight (per shape). Checked against the *local placement rule*, i.e.
O(#placements), never by enumerating tilings.

Decision relevance: no non-negative tile-count vector is consistent with the
total weight of the board, so no tiling can exist. A constant weighting is
structurally valid but never decision-relevant.
"""
from __future__ import annotations

import re
from typing import Any

from ..structures import tiling
from ..utils.safe_expr import UnsafeExpressionError, safe_eval
from .base import CertificateError, StepResult, Verifier, register_verifier

_COORD_RE = re.compile(r"^\s*\(?\s*(-?\d+)\s*[,;\s]\s*(-?\d+)\s*\)?\s*$")


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


def cell_key(cell: tuple[int, int]) -> str:
    return f"{cell[0]},{cell[1]}"


def label_to_cell_map(instance) -> dict[str, tuple[int, int]]:
    """Inverse of ``instance.surface['labels']`` (vertex label -> cell) if present."""
    labels = (instance.surface or {}).get("labels") or {}
    out = {}
    for key, label in labels.items():
        m = _COORD_RE.match(key)
        if m:
            out[str(label)] = (int(m.group(1)), int(m.group(2)))
    return out


def parse_cell(key: Any, label_map: dict[str, tuple[int, int]]) -> tuple[int, int]:
    if isinstance(key, (list, tuple)) and len(key) == 2:
        return (_as_int(key[0], "row"), _as_int(key[1], "column"))
    if isinstance(key, str):
        if key in label_map:
            return label_map[key]
        m = _COORD_RE.match(key)
        if m:
            return (int(m.group(1)), int(m.group(2)))
    raise CertificateError(f"cannot interpret cell reference {key!r}")


def evaluate_weight_expr(expr: str, structure: dict) -> dict[tuple[int, int], int]:
    rows, cols = structure["rows"], structure["cols"]
    weights = {}
    for r, c in tiling.cells(structure):
        env = {"r": r, "c": c, "row": r, "col": c, "i": r, "j": c, "y": r, "x": c, "n": max(rows, cols), "R": rows, "C": cols}
        try:
            value = safe_eval(expr, env)
        except UnsafeExpressionError as e:
            raise CertificateError(f"weight_expr could not be evaluated: {e}") from e
        weights[(r, c)] = _as_int(value, f"weight of cell ({r}, {c})")
    return weights


@register_verifier
class ColoringInvariantVerifier(Verifier):
    certificate_type = "coloring_invariant"
    method = "local_rule"
    exact = True
    supported_structures = ("tiling",)

    def normalize(self, instance, certificate: dict) -> dict:
        structure = instance.structure
        modulus = certificate.get("modulus")
        if modulus is not None:
            modulus = _as_int(modulus, "modulus")
            if modulus < 1:
                raise CertificateError("modulus must be >= 1")
        if certificate.get("weight_expr") is not None:
            expr = certificate["weight_expr"]
            if not isinstance(expr, str) or not expr.strip():
                raise CertificateError("weight_expr must be a non-empty string")
            weights = evaluate_weight_expr(expr, structure)
            source = {"weight_expr": expr}
        elif certificate.get("weights") is not None:
            raw = certificate["weights"]
            label_map = label_to_cell_map(instance)
            items = raw.items() if isinstance(raw, dict) else raw
            weights = {}
            try:
                for key, value in items:
                    weights[parse_cell(key, label_map)] = _as_int(value, f"weight of {key!r}")
            except (TypeError, ValueError) as e:
                raise CertificateError(f"weights must map cells to integers: {e}") from e
            present = tiling.cells(structure)
            missing = [cell for cell in present if cell not in weights]
            if missing:
                raise CertificateError(f"weights missing for {len(missing)} cells, e.g. {missing[:3]}")
            weights = {cell: weights[cell] for cell in present}
            source = {"weights": "table"}
        else:
            raise CertificateError("certificate needs 'weight_expr' or 'weights'")
        return {
            "certificate_type": self.certificate_type,
            "weights": {cell_key(cell): w for cell, w in sorted(weights.items())},
            "modulus": modulus,
            "source": source,
        }

    @staticmethod
    def _weights(cert: dict) -> dict[tuple[int, int], int]:
        out = {}
        for key, w in cert["weights"].items():
            r, c = key.split(",")
            out[(int(r), int(c))] = int(w)
        return out

    @staticmethod
    def _reduce(value: int, modulus) -> int:
        return value % modulus if modulus else value

    def _tile_sums(self, structure: dict, weights: dict, modulus) -> tuple[dict[int, int], int, dict | None]:
        """Per-shape placement sums; returns (sums, n_placements, counterexample_or_None)."""
        placements = tiling.placements(structure)
        tile_sums: dict[int, int] = {}
        for shape_idx, covered in placements:
            s = self._reduce(sum(weights[cell] for cell in covered), modulus)
            if shape_idx not in tile_sums:
                tile_sums[shape_idx] = s
            elif tile_sums[shape_idx] != s:
                return tile_sums, len(placements), {"placement": sorted(covered), "shape": shape_idx, "expected": tile_sums[shape_idx], "found": s}
        return tile_sums, len(placements), None

    def verify_structure(self, instance, cert: dict) -> StepResult:
        weights = self._weights(cert)
        tile_sums, n_placements, counterexample = self._tile_sums(instance.structure, weights, cert["modulus"])
        if n_placements == 0:
            return StepResult(False, "no legal tile placement exists; the invariant is vacuous", {"n_placements": 0})
        if counterexample is not None:
            return StepResult(
                False,
                f"placement {counterexample['placement']} of tile {counterexample['shape']} has weight "
                f"{counterexample['found']}, but another placement has {counterexample['expected']}",
                {"n_placements": n_placements, **counterexample},
            )
        return StepResult(True, None, {"n_placements": n_placements, "tile_sums": tile_sums})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        weights = self._weights(cert)
        modulus = cert["modulus"]
        tile_sums, _, _ = self._tile_sums(structure, weights, modulus)
        sizes = tiling.shape_sizes(structure)
        n_cells = len(tiling.cells(structure))
        total = self._reduce(sum(weights.values()), modulus)
        shapes = sorted(tile_sums)
        consistent = _find_consistent_counts(n_cells, [sizes[i] for i in shapes], [tile_sums[i] for i in shapes], total, modulus)
        details = {"total_weight": total, "tile_sums": tile_sums, "n_cells": n_cells, "consistent_tile_counts": consistent}
        answer = instance.ground_truth.get("answer")
        if consistent is not None:
            if len(set(weights.values())) == 1:
                return StepResult(False, "constant weighting: it cannot separate any two states", details)
            return StepResult(False, f"a tiling with tile counts {consistent} would be consistent with the weighting; it does not rule out a tiling", details)
        if answer == "possible":
            details["inconsistent_with_ground_truth"] = True
            return StepResult(False, "weighting claims impossibility but the instance ground truth is 'possible'", details)
        return StepResult(True, None, details)


def _find_consistent_counts(n_cells: int, sizes: list[int], sums: list[int], total: int, modulus) -> list[int] | None:
    """Non-negative integer counts k with sum(k_i*size_i) == n_cells and
    sum(k_i*sum_i) == total (mod modulus), or None if no such vector exists."""

    def rec(idx: int, remaining_cells: int, acc: int, counts: list[int]):
        if idx == len(sizes):
            if remaining_cells == 0 and (acc % modulus if modulus else acc) == total:
                return list(counts)
            return None
        max_k = remaining_cells // sizes[idx]
        if idx == len(sizes) - 1:
            candidates = [max_k] if max_k * sizes[idx] == remaining_cells else []
        else:
            candidates = range(max_k + 1)
        for k in candidates:
            counts.append(k)
            found = rec(idx + 1, remaining_cells - k * sizes[idx], acc + k * sums[idx], counts)
            counts.pop()
            if found is not None:
                return found
        return None

    return rec(0, n_cells, 0, [])
