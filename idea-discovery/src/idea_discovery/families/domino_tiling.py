"""Domino tiling of a grid with removed cells (seed: the mutilated chessboard).

Structure: ``tiling`` (n x n grid, k removed cells, 1 x 2 dominoes).
Canonical idea: checkerboard weighting w(r, c) = (-1)^(r+c); every domino
has weight 0, so a tileable region has total weight 0.

Instances whose answer is "impossible" are proved by the invariant
(idea_bearing = True). Instances whose answer is "possible" are balance
controls; their ground truth is an explicit tiling found by bipartite
matching (idea_bearing = False). Balanced-but-untileable boards are rejected
at generation time because the canonical idea does not decide them.

Transfer surfaces:
    d0  the classical 8 x 8 chessboard with two opposite corners removed
    d1  n x n grid with listed removed coordinates (+ ASCII picture)
    d2  the same region presented as an abstract graph (random vertex labels,
        edge list); question: perfect pairing along edges
"""
from __future__ import annotations

import random
import re
from typing import Optional

from ..extraction.json_block import find_certificates
from ..structures import tiling
from ..utils.hashing import derive_seed
from .base import CanonicalIdea, ExtractedCertificate, Instance, ProblemFamily, register_family

SURFACES = {0: "classical_chessboard", 1: "grid_coordinates", 2: "graph_cover"}


def _cell_key(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Expand [start, end) to the enclosing sentence (bounded by . ! ? or blank line)."""
    s = start
    while s > 0 and text[s - 1] not in ".!?\n":
        s -= 1
    e = end
    while e < len(text) and text[e] not in ".!?\n":
        e += 1
    return s, min(len(text), e + 1)


@register_family
class DominoTilingFamily(ProblemFamily):
    family_id = "domino_tiling"
    idea_type = "coloring_invariant"
    domain = "combinatorial geometry / tiling"
    size_parameter = "board side n (n x n grid, about n/2 removed cells)"
    certificate_type = "coloring_invariant"
    certificate_types = ("coloring_invariant", "explicit_construction")
    verification_method = "local_rule"
    generation_method = "seeded random removal; ground truth by color imbalance + bipartite matching; rejection sampling for the target answer"
    supported_transfer_levels = (0, 1, 2)
    version = "0.1"

    def __init__(self, possible_fraction: float = 0.35, max_attempts: int = 5000):
        self.possible_fraction = possible_fraction
        self.max_attempts = max_attempts

    # -- generation ------------------------------------------------------
    @staticmethod
    def removal_count(size: int) -> int:
        k = max(2, size // 2)
        if (size * size - k) % 2:
            k += 1
        return k

    def _ground_truth(self, structure: dict) -> dict:
        imbalance = tiling.color_imbalance(structure)
        if imbalance != 0:
            return {"answer": "impossible", "proof_type": "coloring_invariant", "color_imbalance": imbalance, "witness": None}
        matching = tiling.perfect_matching(structure)
        if matching is None:
            return {"answer": "impossible", "proof_type": "other", "color_imbalance": 0, "witness": None}
        witness = {"certificate_type": "explicit_construction", "tiles": [[list(a), list(b)] for a, b in matching]}
        return {"answer": "possible", "proof_type": "explicit_construction", "color_imbalance": 0, "witness": witness}

    def generate_instance(self, size: int, seed: int, answer: Optional[str] = None, **kwargs) -> Instance:
        if size < 3:
            raise ValueError("size must be >= 3")
        rng = random.Random(derive_seed(self.family_id, self.version, size, seed))
        want_possible = (rng.random() < self.possible_fraction) if answer is None else (answer == "possible")
        k = self.removal_count(size)
        all_cells = [(r, c) for r in range(1, size + 1) for c in range(1, size + 1)]
        for _ in range(self.max_attempts):
            removed = rng.sample(all_cells, k)
            structure = tiling.make_structure(size, size, removed)
            gt = self._ground_truth(structure)
            if want_possible and gt["answer"] == "possible":
                break
            if not want_possible and gt["proof_type"] == "coloring_invariant":
                break
        else:  # pragma: no cover
            raise RuntimeError(f"could not generate a {'possible' if want_possible else 'impossible'} instance of size {size}")
        return Instance(
            instance_id=f"{self.family_id}-n{size}-s{seed}-d1",
            family_id=self.family_id,
            size=size,
            transfer_level=1,
            generation_seed=seed,
            structure=structure,
            parameters={"rows": size, "cols": size, "n_removed": k, "tile": "domino"},
            ground_truth=gt,
            idea_bearing=gt["answer"] == "impossible",
            surface={"type": SURFACES[1]},
            transfer={"level": 1, "source_family": self.family_id, "target_surface": SURFACES[1], "preserved_structure": "domino placement graph", "transformation": "seeded random cell removal"},
            family_version=self.version,
        )

    def classical_instance(self) -> Instance:
        structure = tiling.make_structure(8, 8, [(1, 1), (8, 8)])
        gt = self._ground_truth(structure)
        return Instance(
            instance_id=f"{self.family_id}-classical-mutilated-chessboard-d0",
            family_id=self.family_id,
            size=8,
            transfer_level=0,
            generation_seed=0,
            structure=structure,
            parameters={"rows": 8, "cols": 8, "n_removed": 2, "tile": "domino", "name": "mutilated chessboard"},
            ground_truth=gt,
            idea_bearing=True,
            surface={"type": SURFACES[0]},
            transfer={"level": 0, "source_family": self.family_id, "target_surface": SURFACES[0], "preserved_structure": "domino placement graph", "transformation": "none (classical seed problem)"},
            source="classical",
            family_version=self.version,
        )

    def apply_surface(self, instance: Instance, transfer_level: int, seed: int) -> Instance:
        if transfer_level != 2:
            raise ValueError(f"{self.family_id} supports surface change only at level 2")
        rng = random.Random(derive_seed(self.family_id, "surface", transfer_level, seed, instance.instance_id))
        cells = tiling.cells(instance.structure)
        numbers = list(range(1, len(cells) + 1))
        rng.shuffle(numbers)
        labels = {_cell_key(cell): f"v{num}" for cell, num in zip(cells, numbers)}
        edges = [[labels[_cell_key(a)], labels[_cell_key(b)]] for a, b in tiling.adjacency_edges(instance.structure)]
        rng.shuffle(edges)
        for e in edges:
            rng.shuffle(e)
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
            surface={"type": SURFACES[2], "labels": labels, "edges": edges},
            transfer={
                "level": 2,
                "source_family": self.family_id,
                "source_instance_id": instance.instance_id,
                "target_surface": SURFACES[2],
                "preserved_structure": "adjacency graph of remaining cells (bipartite, class imbalance)",
                "transformation": "cells -> randomly labelled vertices; domino placements -> edges; tiling -> perfect pairing",
            },
            source=instance.source,
            family_version=self.version,
        )

    # -- rendering -------------------------------------------------------
    def render_problem(self, instance: Instance, format: str = "text") -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        s = instance.structure
        if surface == SURFACES[0]:
            return (
                "An ordinary 8 x 8 chessboard has two diagonally opposite corner squares removed, "
                "leaving 62 squares. You have 31 dominoes, each of which covers exactly two squares that share an edge. "
                "Can the 62 remaining squares be completely covered by the 31 dominoes, with no overlaps and no domino "
                "sticking out of the board?"
            )
        if surface == SURFACES[1]:
            removed = ", ".join(f"({r}, {c})" for r, c in s["removed"])
            n_cells = s["rows"] * s["cols"] - len(s["removed"])
            text = (
                f"Consider a grid of unit squares with {s['rows']} rows and {s['cols']} columns. Rows are numbered 1 to {s['rows']} from top to bottom "
                f"and columns 1 to {s['cols']} from left to right; the square in row r and column c is written (r, c). "
                f"The following {len(s['removed'])} squares have been removed from the grid: {removed}.\n\n"
                f"A domino is a 1 x 2 tile that covers exactly two squares sharing an edge. Can the {n_cells} remaining squares "
                f"be completely covered by non-overlapping dominoes, with every domino lying entirely on remaining squares?"
            )
            if format == "text" and s["rows"] <= 20:
                text += "\n\nPicture of the grid ('.' = remaining square, 'X' = removed square), rows top to bottom:\n" + tiling.ascii_board(s)
            return text
        if surface == SURFACES[2]:
            labels = instance.surface["labels"]
            names = sorted(labels.values(), key=lambda v: int(v[1:]))
            edges = ", ".join(f"{a}-{b}" for a, b in instance.surface["edges"])
            return (
                f"A graph has {len(names)} vertices, labelled {names[0]} to {names[-1]}, and the following {len(instance.surface['edges'])} edges "
                f"(each written as a pair of adjacent vertices):\n{edges}.\n\n"
                "Is it possible to partition the set of all vertices into pairs so that the two vertices in each pair are joined by an edge?"
            )
        raise ValueError(f"unknown surface {surface!r}")

    # -- mathematics -----------------------------------------------------
    def solve_ground_truth(self, instance: Instance) -> dict:
        return self._ground_truth(instance.structure)

    def canonical_idea(self, instance: Instance) -> CanonicalIdea:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            labels = instance.surface["labels"]
            weights = {label: tiling.checkerboard_weight(tuple(int(x) for x in key.split(","))) for key, label in labels.items()}
            plus = sorted((l for l, w in weights.items() if w == 1), key=lambda v: int(v[1:]))
            minus = sorted((l for l, w in weights.items() if w == -1), key=lambda v: int(v[1:]))
            prose = (
                "The vertices can be split into two classes so that every edge joins a vertex of one class to a vertex of the other class "
                "(assign classes by alternating along edges). Each pair of a perfect pairing uses exactly one vertex from each class, "
                "so a perfect pairing can exist only if the two classes have the same number of vertices. Compare the class sizes."
            )
            explicit = prose + f"\nClass 1: {{{', '.join(plus)}}}.\nClass 2: {{{', '.join(minus)}}}."
            return CanonicalIdea(prose, {"certificate_type": "coloring_invariant", "weights": weights}, "coloring_invariant", "bipartition imbalance", explicit)
        prose = (
            "Give every square (r, c) the weight (-1)^(r + c), i.e. colour the grid like a checkerboard with the two colours "
            "having weights +1 and -1. Every domino covers two squares that share an edge, which always have opposite colours, "
            "so every domino has total weight 0. Hence any region that can be tiled by dominoes has total weight 0: it must contain "
            "equally many squares of each colour. Compare the numbers of remaining squares of the two colours."
        )
        return CanonicalIdea(prose, {"certificate_type": "coloring_invariant", "weight_expr": "(-1)**(r + c)"}, "coloring_invariant", "checkerboard coloring", prose)

    def alternative_idea(self, instance: Instance) -> Optional[CanonicalIdea]:
        # On a connected bipartite region every domino-constant weighting is affine in the
        # checkerboard weighting, so the only 'alternatives' are rescalings; they match the
        # canonical partition and are reported as canonical_match=True.
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            return None
        prose = "Colour square (r, c) black when r + c is even and white otherwise; each domino covers one black and one white square."
        return CanonicalIdea(prose, {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, "coloring_invariant", "0/1 checkerboard", prose)

    def invalid_idea(self, instance: Instance) -> dict:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            labels = instance.surface["labels"]
            # weight by row parity: vertical edges then have sum 1, horizontal edges 0 or 2
            return {"certificate_type": "coloring_invariant", "weights": {label: int(key.split(",")[0]) % 2 for key, label in labels.items()}}
        return {"certificate_type": "coloring_invariant", "weight_expr": "c % 2"}

    def canonical_match(self, instance: Instance, normalized_certificate: dict) -> bool:
        if normalized_certificate.get("certificate_type") != "coloring_invariant":
            return False
        by_color: dict[int, set] = {0: set(), 1: set()}
        for key, w in normalized_certificate["weights"].items():
            r, c = (int(x) for x in key.split(","))
            by_color[(r + c) % 2].add(w)
        return len(by_color[0]) == 1 and len(by_color[1]) == 1 and by_color[0] != by_color[1]

    # -- structured-output schemas (conditions B and C only) ---------------
    def certificate_schema_text(self, instance: Instance) -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            main = (
                '{"certificate_type": "coloring_invariant", "weights": {"<vertex label>": <integer>, ...}}\n'
                "  - give an integer weight for EVERY vertex; the claim is that every edge has the same total weight,\n"
                "    and that the total weight of all vertices is incompatible with a perfect pairing."
            )
            witness = '{"certificate_type": "explicit_construction", "tiles": [["<label>", "<label>"], ...]}  - an explicit perfect pairing.'
        else:
            main = (
                '{"certificate_type": "coloring_invariant", "weight_expr": "<arithmetic expression in r and c>", "modulus": <integer or null>}\n'
                "  - weight_expr gives the weight of square (r, c) (1-based), e.g. \"(r + c) % 2\" or \"(-1)**(r + c)\"; the claim is that\n"
                "    every domino placement has the same total weight (modulo the modulus if given) and that the total weight of the\n"
                "    remaining squares is incompatible with a tiling."
            )
            witness = '{"certificate_type": "explicit_construction", "tiles": [[[r1, c1], [r2, c2]], ...]}  - an explicit complete tiling.'
        return (
            "Use exactly one of the following JSON schemas:\n"
            f"{main}\n{witness}\n"
            '{"certificate_type": "none"}  - if no such principle was used.'
        )

    # -- deterministic extraction ------------------------------------------
    _FORMULA_PATTERNS = [
        ("sum_parity_formula", re.compile(r"\(\s*([a-zA-Z])\s*\+\s*([a-zA-Z])\s*\)\s*(?:mod|%|modulo)\s*2", re.IGNORECASE)),
        ("sum_parity_phrase", re.compile(r"\b([a-zA-Z])\s*\+\s*([a-zA-Z])\s+(?:is|being|are)\s+(?:even|odd)\b", re.IGNORECASE)),
        ("minus_one_power", re.compile(r"\(\s*[-−]\s*1\s*\)\s*(?:\^|\*\*)\s*\(?\s*([a-zA-Z])\s*\+\s*([a-zA-Z])", re.IGNORECASE)),
    ]
    _CHECKERBOARD_RE = re.compile(r"\b(checker[- ]?board|chess[- ]?board)\b", re.IGNORECASE)
    _ALTERNATING_RE = re.compile(r"\balternat\w*\b[^.\n]{0,60}\b(black|white|colou?r)", re.IGNORECASE)
    _COLOR_CONTEXT_RE = re.compile(r"\b(colou?r\w*|paint\w*|pattern|fashion|manner|shade\w*|black|white)\b", re.IGNORECASE)

    def extract_candidates(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        out: list[ExtractedCertificate] = []
        for hit in find_certificates(response):
            if hit.obj.get("certificate_type") in self.certificate_types:
                out.append(ExtractedCertificate(hit.obj, hit.text, hit.start, hit.end, "json_block", "json_block"))
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        if surface == SURFACES[2]:
            out.extend(self._extract_label_sets(instance, response))
            return out
        seen_exprs = {c.certificate.get("weight_expr") for c in out}
        for rule_id, pattern in self._FORMULA_PATTERNS:
            m = pattern.search(response)
            if m:
                a, b = m.group(1).lower(), m.group(2).lower()
                if a != b:
                    s, e = _sentence_span(response, m.start(), m.end())
                    expr = "(-1)**(r + c)" if rule_id == "minus_one_power" else "(r + c) % 2"
                    if expr not in seen_exprs:
                        seen_exprs.add(expr)
                        out.append(ExtractedCertificate({"certificate_type": "coloring_invariant", "weight_expr": expr}, response[s:e], s, e, f"deterministic:{rule_id}", rule_id))
        m = self._CHECKERBOARD_RE.search(response)
        if m:
            s, e = _sentence_span(response, m.start(), m.end())
            if self._COLOR_CONTEXT_RE.search(response[s:e]) and "(r + c) % 2" not in seen_exprs:
                out.append(ExtractedCertificate({"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, response[s:e], s, e, "deterministic:checkerboard_phrase", "checkerboard_phrase"))
                seen_exprs.add("(r + c) % 2")
        elif (m := self._ALTERNATING_RE.search(response)) and "(r + c) % 2" not in seen_exprs:
            s, e = _sentence_span(response, m.start(), m.end())
            out.append(ExtractedCertificate({"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, response[s:e], s, e, "deterministic:alternating_colours_phrase", "alternating_colours_phrase"))
        return out

    def _extract_label_sets(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        """Find an explicitly listed vertex class {v3, v17, ...} and turn it into a +1/-1 weighting."""
        labels = set(instance.surface["labels"].values())
        run_re = re.compile(r"v\d+(?:\s*,\s*v\d+){2,}")
        best = None
        for m in run_re.finditer(response):
            names = [t.strip() for t in m.group(0).split(",")]
            names_set = set(names)
            if not names_set <= labels or names_set == labels:
                continue
            if best is None or len(names_set) > len(best[0]):
                best = (names_set, m.start(), m.end())
        if best is None:
            return []
        chosen, start, end = best
        weights = {label: (1 if label in chosen else -1) for label in labels}
        return [ExtractedCertificate({"certificate_type": "coloring_invariant", "weights": weights}, response[start:end], start, end, "deterministic:label_set_partition", "label_set_partition")]
