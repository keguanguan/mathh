"""Explicit constructions (witnesses) for 'possible' answers.

These are *not* ideas: a complete tiling or a move sequence certifies the
answer without expressing a reusable law. The verifier therefore sets
``is_idea = False`` so that analysis never counts a witness as I = 1.

Certificate forms (JSON):

    {"certificate_type": "explicit_construction",
     "tiles": [[[1, 1], [1, 2]], ["P3", "P17"], ...]}     # tiling structures

    {"certificate_type": "explicit_construction",
     "moves": [1, 3, 3, 2]}                               # 1-based operation numbers (vector games)

    {"certificate_type": "explicit_construction",
     "tiles_moved": [7, 3, 3, 12]}                        # sliding puzzles: the tile slid at each step

    {"certificate_type": "explicit_construction",
     "differences": [[60, 36], [36, 24]]}                  # difference boards: pairs whose difference is written
"""
from __future__ import annotations

from ..structures import difference_board as db, sliding_puzzle as sp, tiling, vector_game as vg
from .base import CertificateError, StepResult, Verifier, register_verifier
from .coloring_invariant import _as_int, label_to_cell_map, parse_cell


@register_verifier
class ExplicitConstructionVerifier(Verifier):
    certificate_type = "explicit_construction"
    method = "exhaustive"  # the witness itself is checked in full
    exact = True
    is_idea = False
    supported_structures = ("tiling", "vector_game", "sliding_puzzle", "difference_board")

    def normalize(self, instance, certificate: dict) -> dict:
        kind = instance.structure["kind"]
        if kind == "tiling":
            raw = certificate.get("tiles")
            if not isinstance(raw, list) or not raw:
                raise CertificateError("tiling witness needs a non-empty 'tiles' list")
            label_map = label_to_cell_map(instance)
            tiles = []
            for tile in raw:
                if not isinstance(tile, (list, tuple)):
                    raise CertificateError(f"tile {tile!r} is not a list of cells")
                tiles.append(sorted(parse_cell(cell, label_map) for cell in tile))
            return {"certificate_type": self.certificate_type, "tiles": tiles}
        if kind == "vector_game":
            raw = certificate.get("moves")
            if not isinstance(raw, list):
                raise CertificateError("move-sequence witness needs a 'moves' list of 1-based operation numbers")
            n_moves = len(instance.structure["moves"])
            moves = [_as_int(m, "move index") for m in raw]
            bad = [m for m in moves if not 1 <= m <= n_moves]
            if bad:
                raise CertificateError(f"move indices must be in 1..{n_moves}; got {bad[:3]}")
            return {"certificate_type": self.certificate_type, "moves": moves}
        if kind == "sliding_puzzle":
            raw = certificate.get("tiles_moved", certificate.get("moves"))
            if not isinstance(raw, list):
                raise CertificateError("sliding-puzzle witness needs a 'tiles_moved' list (tile values slid, in order)")
            return {"certificate_type": self.certificate_type, "tiles_moved": [_as_int(t, "tile") for t in raw]}
        if kind == "difference_board":
            raw = certificate.get("differences", certificate.get("moves"))
            if not isinstance(raw, list):
                raise CertificateError("difference-board witness needs a 'differences' list of [a, b] pairs")
            pairs = []
            for pair in raw:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise CertificateError(f"{pair!r} is not a pair")
                pairs.append([_as_int(pair[0], "number"), _as_int(pair[1], "number")])
            return {"certificate_type": self.certificate_type, "differences": pairs}
        raise CertificateError(f"unsupported structure {kind!r}")

    def verify_structure(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        if structure["kind"] == "tiling":
            legal = {covered for _, covered in tiling.placements(structure)}
            covered_all: set = set()
            for tile in cert["tiles"]:
                fs = frozenset(tile)
                if fs not in legal:
                    return StepResult(False, f"{tile} is not a legal tile placement", {"bad_tile": tile})
                if covered_all & fs:
                    return StepResult(False, f"tile {tile} overlaps an earlier tile", {"bad_tile": tile})
                covered_all |= fs
            return StepResult(True, None, {"n_tiles": len(cert["tiles"])})
        if structure["kind"] == "sliding_puzzle":
            try:
                final = sp.apply_tile_moves(structure, sp.to_grid(structure["start"]), cert["tiles_moved"])
            except ValueError as e:
                return StepResult(False, f"illegal move: {e}", {})
            return StepResult(True, None, {"final": [list(r) for r in final], "n_steps": len(cert["tiles_moved"])})
        if structure["kind"] == "difference_board":
            board = set(structure["numbers"])
            for step, (a, b) in enumerate(cert["differences"]):
                if a not in board or b not in board:
                    return StepResult(False, f"step {step + 1}: {a} or {b} is not on the board", {"step": step + 1})
                z = db.apply(structure["operation"], a, b)
                if z <= 0 or z in board:
                    return StepResult(False, f"step {step + 1}: |{a} - {b}| = {z} is not a legal new number", {"step": step + 1})
                board.add(z)
            return StepResult(True, None, {"n_steps": len(cert["differences"]), "final_board": sorted(board)})
        state = tuple(structure["initial"])
        for step, idx in enumerate(cert["moves"]):
            nxt = vg.apply_move(state, structure["moves"][idx - 1])
            if nxt is None:
                return StepResult(False, f"operation {idx} is not applicable at step {step + 1} (state {list(state)})", {"step": step + 1, "state": list(state)})
            state = nxt
        return StepResult(True, None, {"final_state": list(state), "n_steps": len(cert["moves"])})

    def verify_relevance(self, instance, cert: dict) -> StepResult:
        structure = instance.structure
        answer = instance.ground_truth.get("answer")
        if structure["kind"] == "tiling":
            covered = {cell for tile in cert["tiles"] for cell in tile}
            missing = [cell for cell in tiling.cells(structure) if cell not in covered]
            if missing:
                return StepResult(False, f"{len(missing)} cells are not covered, e.g. {missing[:3]}", {"n_missing": len(missing)})
            details = {"establishes": "possible"}
        elif structure["kind"] == "sliding_puzzle":
            final = sp.apply_tile_moves(structure, sp.to_grid(structure["start"]), cert["tiles_moved"])
            if final != sp.to_grid(structure["target"]):
                return StepResult(False, "the move sequence does not end in the target arrangement", {"final": [list(r) for r in final]})
            details = {"establishes": "possible"}
        elif structure["kind"] == "difference_board":
            board = set(structure["numbers"])
            for a, b in cert["differences"]:
                board.add(db.apply(structure["operation"], a, b))
            if structure["target"] not in board:
                return StepResult(False, "the target number is never written", {})
            details = {"establishes": "possible"}
        else:
            state = tuple(structure["initial"])
            for idx in cert["moves"]:
                state = vg.apply_move(state, structure["moves"][idx - 1])
            if list(state) not in structure["targets"]:
                return StepResult(False, f"final state {list(state)} is not a target state", {"final_state": list(state)})
            details = {"establishes": "possible", "final_state": list(state)}
        if answer != "possible":
            details["inconsistent_with_ground_truth"] = True
        return StepResult(True, None, details)
