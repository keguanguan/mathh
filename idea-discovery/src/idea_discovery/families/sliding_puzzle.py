"""Sliding puzzle reachability (seed: the 14-15 puzzle, corpus id ``fifteen_puzzle``).

Structure: ``sliding_puzzle`` (n x n grid, tiles 1..n^2-1 and a blank).
Canonical idea: sign of the permutation of all cells (blank included),
corrected by the parity of the blank's taxicab distance, is invariant.

Ground truth is the parity rule, which is exact on rectangular boards with at
least two rows and two columns (the reachable set is exactly one parity class).
Tests confirm this exhaustively on 2 x 3 and 3 x 3 boards.

Instances: start = random arrangement; "possible" targets are produced by a
long random walk (witness = the tiles slid), "impossible" targets by
additionally swapping two tiles (flips the parity class).

Transfer surfaces:
    d0  the classical 4 x 4 puzzle with 14 and 15 swapped
    d1  n x n grid of numbered tiles with a blank
    d2  tokens on the vertices of a graph (random labels, listed order fixes the
        reading order), one vertex empty; a token moves along an edge into the empty vertex
"""
from __future__ import annotations

import random
import re
from typing import Optional

from ..extraction.json_block import find_certificates
from ..generation.seeds import seed_provenance, seed_statement
from ..structures import sliding_puzzle as sp
from ..utils.hashing import derive_seed
from .base import CanonicalIdea, ExtractedCertificate, Instance, ProblemFamily, register_family

SURFACES = {0: "classical_fifteen", 1: "numbered_tiles", 2: "graph_tokens"}
SEED_ID = "fifteen_puzzle"


def _cell_key(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    s = start
    while s > 0 and text[s - 1] not in ".!?\n":
        s -= 1
    e = end
    while e < len(text) and text[e] not in ".!?\n":
        e += 1
    return s, min(len(text), e + 1)


def _grid_text(grid, blank: str = "_") -> str:
    width = max(len(str(v)) for row in grid for v in row)
    return "\n".join("  ".join((blank if v == 0 else str(v)).rjust(width) for v in row) for row in grid)


@register_family
class SlidingPuzzleFamily(ProblemFamily):
    family_id = "sliding_puzzle"
    idea_type = "permutation_parity"
    domain = "permutation puzzles / group actions"
    size_parameter = "board side n (n x n, n^2 - 1 tiles)"
    certificate_type = "permutation_parity"
    certificate_types = ("permutation_parity", "explicit_construction")
    verification_method = "local_rule"
    generation_method = "random start; target by seeded random walk (possible) or walk + tile swap (impossible); parity-rule ground truth"
    supported_transfer_levels = (0, 1, 2)
    version = "0.1"

    def __init__(self, possible_fraction: float = 0.35, walk_factor: int = 20):
        self.possible_fraction = possible_fraction
        self.walk_factor = walk_factor

    # -- generation ------------------------------------------------------
    def _ground_truth(self, structure: dict, witness_tiles: Optional[list[int]]) -> dict:
        if sp.parity_reachable(structure):
            witness = {"certificate_type": "explicit_construction", "tiles_moved": witness_tiles} if witness_tiles is not None else None
            return {"answer": "possible", "proof_type": "explicit_construction", "witness": witness, "parity_start": sp.canonical_invariant(structure, sp.to_grid(structure["start"]))}
        return {"answer": "impossible", "proof_type": "permutation_parity", "witness": None, "parity_start": sp.canonical_invariant(structure, sp.to_grid(structure["start"]))}

    def generate_instance(self, size: int, seed: int, answer: Optional[str] = None, **kwargs) -> Instance:
        if size < 3:
            raise ValueError("size must be >= 3")
        rng = random.Random(derive_seed(self.family_id, self.version, size, seed))
        want_possible = (rng.random() < self.possible_fraction) if answer is None else (answer == "possible")
        values = list(range(size * size))
        rng.shuffle(values)
        start = sp.to_grid([values[i * size : (i + 1) * size] for i in range(size)])
        probe = sp.make_structure(size, size, start, start)
        target, tiles = sp.random_walk(probe, start, self.walk_factor * size * size, rng)
        if not want_possible:
            flat = [v for row in target for v in row if v != 0]
            a, b = rng.sample(flat, 2)
            target = sp.to_grid([[b if v == a else a if v == b else v for v in row] for row in target])
            tiles = None
        structure = sp.make_structure(size, size, start, target)
        gt = self._ground_truth(structure, tiles)
        assert (gt["answer"] == "possible") == want_possible
        return Instance(
            instance_id=f"{self.family_id}-n{size}-s{seed}-d1",
            family_id=self.family_id,
            size=size,
            transfer_level=1,
            generation_seed=seed,
            structure=structure,
            parameters={"rows": size, "cols": size, "n_tiles": size * size - 1, **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=gt["answer"] == "impossible",
            surface={"type": SURFACES[1]},
            transfer={"level": 1, "source_family": self.family_id, "target_surface": SURFACES[1], "preserved_structure": "token sliding on the grid graph", "transformation": "random start, random-walk target (+ tile swap)"},
            family_version=self.version,
        )

    def classical_instance(self) -> Instance:
        solved = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 0]]
        swapped = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 15, 14, 0]]
        structure = sp.make_structure(4, 4, solved, swapped)
        gt = self._ground_truth(structure, None)
        return Instance(
            instance_id=f"{self.family_id}-classical-fifteen-d0",
            family_id=self.family_id,
            size=4,
            transfer_level=0,
            generation_seed=0,
            structure=structure,
            parameters={"rows": 4, "cols": 4, "n_tiles": 15, "name": "Sam Loyd's 14-15 puzzle", **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=True,
            surface={"type": SURFACES[0]},
            transfer={"level": 0, "source_family": self.family_id, "target_surface": SURFACES[0], "preserved_structure": "token sliding on the grid graph", "transformation": "none (classical seed problem)"},
            source="classical",
            family_version=self.version,
        )

    def apply_surface(self, instance: Instance, transfer_level: int, seed: int) -> Instance:
        if transfer_level != 2:
            raise ValueError(f"{self.family_id} supports surface change only at level 2")
        rng = random.Random(derive_seed(self.family_id, "surface", transfer_level, seed, instance.instance_id))
        cells = sp.cells(instance.structure)
        numbers = list(range(1, len(cells) + 1))
        rng.shuffle(numbers)
        labels = {_cell_key(cell): f"v{num}" for cell, num in zip(cells, numbers)}
        edges = [[labels[_cell_key(a)], labels[_cell_key(b)]] for a, b in sp.edges(instance.structure)]
        rng.shuffle(edges)
        for e in edges:
            rng.shuffle(e)
        n_tiles = len(cells) - 1
        token_names = list(range(1, n_tiles + 1))
        return Instance(
            instance_id=instance.instance_id[: -len("-d1")] + "-d2" if instance.instance_id.endswith("-d1") else instance.instance_id + "-d2",
            family_id=self.family_id,
            size=instance.size,
            transfer_level=2,
            generation_seed=seed,
            structure=instance.structure,
            parameters=dict(instance.parameters, n_vertices=len(cells), n_edges=len(edges)),
            ground_truth=instance.ground_truth,
            idea_bearing=instance.idea_bearing,
            surface={"type": SURFACES[2], "labels": labels, "edges": edges, "token_names": token_names},
            transfer={
                "level": 2,
                "source_family": self.family_id,
                "source_instance_id": instance.instance_id,
                "target_surface": SURFACES[2],
                "preserved_structure": "token sliding on the grid graph (bipartite); permutation parity",
                "transformation": "cells -> randomly labelled vertices in reading order; adjacency -> edges; tiles -> tokens",
            },
            source=instance.source,
            family_version=self.version,
        )

    # -- rendering -------------------------------------------------------
    def _listing_order(self, instance: Instance) -> list[str]:
        labels = instance.surface["labels"]
        return [labels[_cell_key(cell)] for cell in sp.cells(instance.structure)]

    def render_problem(self, instance: Instance, format: str = "text") -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        s = instance.structure
        if surface == SURFACES[0]:
            text = seed_statement(SEED_ID)
            return text or (
                "Fifteen numbered tiles sit in a 4 x 4 frame with one empty cell. A move slides a tile adjacent to the empty cell into it. "
                "Starting from the ordered arrangement 1, 2, ..., 15 with the blank in the bottom-right corner, can one reach the arrangement "
                "in which only tiles 14 and 15 are swapped (blank again bottom-right)?"
            )
        if surface == SURFACES[1]:
            n = s["rows"] * s["cols"] - 1
            return (
                f"A {s['rows']} x {s['cols']} frame holds {n} square tiles numbered 1 to {n} and one empty cell. A move slides a tile that is "
                "horizontally or vertically adjacent to the empty cell into the empty cell (the tile's old cell becomes empty). "
                "Arrangements are written row by row from top to bottom, with '_' marking the empty cell.\n\n"
                f"Starting arrangement:\n{_grid_text(s['start'])}\n\nTarget arrangement:\n{_grid_text(s['target'])}\n\n"
                "Is it possible to reach the target arrangement from the starting arrangement by a sequence of moves?"
            )
        if surface == SURFACES[2]:
            order = self._listing_order(instance)
            labels = instance.surface["labels"]
            start_grid, target_grid = sp.to_grid(s["start"]), sp.to_grid(s["target"])

            def placement(grid):
                parts = []
                for cell in sp.cells(s):
                    v = grid[cell[0] - 1][cell[1] - 1]
                    parts.append(f"{labels[_cell_key(cell)]}: {'empty' if v == 0 else 'token ' + str(v)}")
                return ", ".join(parts)

            edges = ", ".join(f"{a}-{b}" for a, b in instance.surface["edges"])
            n_tokens = len(order) - 1
            return (
                f"A graph has {len(order)} vertices, listed in the fixed order {', '.join(order)}, and the following {len(instance.surface['edges'])} edges: {edges}.\n\n"
                f"{n_tokens} tokens numbered 1 to {n_tokens} are placed on distinct vertices, so exactly one vertex is empty. A move takes a token on a vertex "
                "adjacent (by an edge) to the empty vertex and moves it to the empty vertex; the token's old vertex becomes empty.\n\n"
                f"Starting placement: {placement(start_grid)}.\n\nTarget placement: {placement(target_grid)}.\n\n"
                "Is it possible to reach the target placement from the starting placement by a sequence of moves?"
            )
        raise ValueError(f"unknown surface {surface!r}")

    # -- mathematics -----------------------------------------------------
    def solve_ground_truth(self, instance: Instance) -> dict:
        witness = instance.ground_truth.get("witness")
        return self._ground_truth(instance.structure, witness["tiles_moved"] if witness else None)

    def canonical_idea(self, instance: Instance) -> CanonicalIdea:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            labels = instance.surface["labels"]
            weights = {label: (int(k.split(",")[0]) + int(k.split(",")[1])) % 2 for k, label in labels.items()}
            zero = [l for l, w in weights.items() if w == 0]
            one = [l for l, w in weights.items() if w == 1]
            prose = (
                "Read the contents of the vertices in the listed order, treating the empty vertex as an extra token with the largest number, "
                "as a permutation. Every move swaps that extra token with a neighbouring token, so it is a single transposition and flips the "
                "sign of the permutation. The graph is bipartite: split its vertices into two classes so that every edge joins the classes; "
                "each move also moves the empty vertex from one class to the other. Hence sign(permutation) x (-1)^(class of the empty vertex) "
                "never changes. Compare its value in the starting and target placements."
            )
            explicit = prose + f"\nClass 0: {{{', '.join(sorted(zero, key=lambda v: int(v[1:])))}}}.\nClass 1: {{{', '.join(sorted(one, key=lambda v: int(v[1:])))}}}."
            return CanonicalIdea(prose, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_weights": weights}, "permutation_parity", "permutation sign x blank class", explicit)
        prose = (
            "Read the cells row by row, treating the empty cell as an extra tile numbered one more than the largest tile, as a permutation. "
            "Every move swaps the empty cell with an adjacent tile, so it is a single transposition and flips the sign of the permutation; "
            "at the same time the empty cell moves one step, so the parity of its taxicab distance from a fixed corner (row + column) also flips. "
            "Hence sign(permutation) x (-1)^(row + column of the empty cell) never changes. Compare its value in the starting and target arrangements."
        )
        return CanonicalIdea(prose, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "taxicab"}, "permutation_parity", "permutation sign x blank taxicab parity", prose)

    def alternative_idea(self, instance: Instance) -> Optional[CanonicalIdea]:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            return None
        cols = instance.structure["cols"]
        if cols % 2 == 1:
            prose = "Count the inversions among the tiles only (ignoring the empty cell), reading row by row. Because the width is odd, every move changes this count by an even number, so its parity never changes."
            cert = {"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "none"}
        else:
            prose = "Count the inversions among the tiles only (ignoring the empty cell), reading row by row, and add the row number of the empty cell. Every move changes this sum by an even number, so its parity never changes."
            cert = {"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "row"}
        return CanonicalIdea(prose, cert, "permutation_parity", "tile inversions (+ blank row)", prose)

    def invalid_idea(self, instance: Instance) -> dict:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            labels = instance.surface["labels"]
            return {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_weights": {label: 0 for label in labels.values()}}
        return {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "none"}

    def canonical_match(self, instance: Instance, normalized_certificate: dict) -> bool:
        if normalized_certificate.get("certificate_type") != "permutation_parity" or normalized_certificate.get("permutation_of") != "all_cells":
            return False
        w = normalized_certificate["blank_weight"]
        canon = {f"{r},{c}": (r + c) % 2 for r, c in sp.cells(instance.structure)}
        return all(w[k] == canon[k] for k in canon) or all(w[k] != canon[k] for k in canon)

    # -- structured-output schemas (conditions B and C only) ---------------
    def certificate_schema_text(self, instance: Instance) -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            main = (
                '{"certificate_type": "permutation_parity", "permutation_of": "all_cells" | "tiles_only", "blank_weights": {"<vertex label>": 0 or 1, ...}}\n'
                "  - the claim: (inversion parity of the tokens read in the listed vertex order, with the empty vertex read as the largest token if\n"
                '    "all_cells" or omitted if "tiles_only") + (weight of the empty vertex), taken mod 2, is unchanged by every move, and differs\n'
                "    between the starting and target placements. Give a weight for EVERY vertex."
            )
            witness = '{"certificate_type": "explicit_construction", "tiles_moved": [<token number moved at each step>, ...]}  - an explicit move sequence.'
        else:
            main = (
                '{"certificate_type": "permutation_parity", "permutation_of": "all_cells" | "tiles_only", "blank_term": "taxicab" | "row" | "col" | "none"}\n'
                "  - the claim: (inversion parity of the arrangement read row by row, with the empty cell read as tile n^2 if \"all_cells\" or omitted\n"
                '    if "tiles_only") + (parity of the chosen quantity of the empty cell: row + column, row, column, or nothing), taken mod 2,\n'
                "    is unchanged by every move and differs between start and target. Instead of blank_term you may give\n"
                '    "blank_expr": "<0/1 expression in r and c (1-based) for the empty cell>".'
            )
            witness = '{"certificate_type": "explicit_construction", "tiles_moved": [<tile number slid at each step>, ...]}  - an explicit move sequence.'
        return "Use exactly one of the following JSON schemas:\n" + main + "\n" + witness + '\n{"certificate_type": "none"}  - if no such principle was used.'

    # -- deterministic extraction ------------------------------------------
    _SIGN_RE = re.compile(r"\b(sign|parity)\s+of\s+(the\s+)?permutation\b|\bpermutation\b[^.\n]{0,40}\b(sign|parity|odd|even)\b|\b(odd|even)\s+permutation\b", re.IGNORECASE)
    _INVERSION_RE = re.compile(r"\binversions?\b", re.IGNORECASE)
    _TAXICAB_RE = re.compile(r"\b(taxicab|manhattan|row\s*\+\s*col(umn)?|r\s*\+\s*c\b|distance\s+of\s+the\s+(blank|empty|hole)|(blank|empty|hole)[^.\n]{0,40}\bdistance|colou?r\s+of\s+the\s+(blank|empty|hole)|(blank|empty|hole)[^.\n]{0,40}\b(checkerboard|chessboard|bipartite|class))", re.IGNORECASE)
    _ROW_RE = re.compile(r"\brow\s+(of|containing|number\s+of)\s+the\s+(blank|empty|hole)|\b(blank|empty|hole)[^.\n]{0,25}\brow\b", re.IGNORECASE)

    def extract_candidates(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        out: list[ExtractedCertificate] = []
        for hit in find_certificates(response):
            if hit.obj.get("certificate_type") in self.certificate_types:
                out.append(ExtractedCertificate(hit.obj, hit.text, hit.start, hit.end, "json_block", "json_block"))
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        sign = self._SIGN_RE.search(response)
        inv = self._INVERSION_RE.search(response)
        if surface == SURFACES[2]:
            if sign or inv:
                out.extend(self._extract_label_sets(instance, response, sign or inv))
            return out
        taxi = self._TAXICAB_RE.search(response)
        row = self._ROW_RE.search(response)
        if sign and taxi:
            m = sign
            s, e = _sentence_span(response, min(m.start(), taxi.start()), max(m.end(), taxi.end()))
            out.append(ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "taxicab"}, response[s:e], s, e, "deterministic:sign_and_blank_distance", "sign_and_blank_distance"))
        elif inv and row:
            s, e = _sentence_span(response, min(inv.start(), row.start()), max(inv.end(), row.end()))
            out.append(ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "row"}, response[s:e], s, e, "deterministic:inversions_plus_blank_row", "inversions_plus_blank_row"))
        elif inv and taxi:
            s, e = _sentence_span(response, min(inv.start(), taxi.start()), max(inv.end(), taxi.end()))
            out.append(ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "taxicab"}, response[s:e], s, e, "deterministic:inversions_and_blank_distance", "inversions_and_blank_distance"))
        elif inv:
            s, e = _sentence_span(response, inv.start(), inv.end())
            out.append(ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "none"}, response[s:e], s, e, "deterministic:inversions_only", "inversions_only"))
        elif sign:
            s, e = _sentence_span(response, sign.start(), sign.end())
            out.append(ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "none"}, response[s:e], s, e, "deterministic:sign_only", "sign_only"))
        return out

    def _extract_label_sets(self, instance: Instance, response: str, anchor) -> list[ExtractedCertificate]:
        labels = set(instance.surface["labels"].values())
        run_re = re.compile(r"v\d+(?:\s*,\s*v\d+){2,}")
        best = None
        for m in run_re.finditer(response):
            names = {t.strip() for t in m.group(0).split(",")}
            if not names <= labels or names == labels:
                continue
            if best is None or len(names) > len(best[0]):
                best = (names, m.start(), m.end())
        if best is None:
            return []
        chosen, start, end = best
        weights = {label: (1 if label in chosen else 0) for label in labels}
        s, e = _sentence_span(response, anchor.start(), anchor.end())
        span = response[s:e] + " | " + response[start:end]
        return [ExtractedCertificate({"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_weights": weights}, span, min(s, start), max(e, end), "deterministic:sign_and_label_set", "sign_and_label_set")]
