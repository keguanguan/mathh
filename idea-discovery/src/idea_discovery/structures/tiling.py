"""Tiling structure: a finite set of grid cells and a set of polyomino tiles.

structure = {
    "kind": "tiling",
    "rows": R, "cols": C,
    "removed": [[r, c], ...],          # 1-based coordinates
    "tiles": [[[0, 0], [0, 1]], ...],  # tile shapes as offset lists
    "allow_rotations": True,
}

Cells are 1-based ``(row, col)`` tuples. A *placement* is a frozenset of
cells covered by one tile in one legal position. Enumerating placements
costs O(#cells * #shapes * #orientations); it never enumerates tilings.
"""
from __future__ import annotations

import sys
from typing import Iterable

Cell = tuple[int, int]
Shape = tuple[Cell, ...]

DOMINO: list[list[list[int]]] = [[[0, 0], [0, 1]]]


def make_structure(rows: int, cols: int, removed: Iterable[Cell], tiles=None, allow_rotations=True) -> dict:
    return {
        "kind": "tiling",
        "rows": int(rows),
        "cols": int(cols),
        "removed": sorted([list(map(int, cell)) for cell in removed]),
        "tiles": tiles if tiles is not None else [list(map(list, s)) for s in DOMINO],
        "allow_rotations": bool(allow_rotations),
    }


def removed_cells(structure: dict) -> set[Cell]:
    return {(int(r), int(c)) for r, c in structure["removed"]}


def cells(structure: dict) -> list[Cell]:
    """All remaining cells in row-major order."""
    removed = removed_cells(structure)
    return [
        (r, c)
        for r in range(1, structure["rows"] + 1)
        for c in range(1, structure["cols"] + 1)
        if (r, c) not in removed
    ]


def _normalize_shape(shape: Iterable[Iterable[int]]) -> Shape:
    pts = [(int(a), int(b)) for a, b in shape]
    min_r = min(p[0] for p in pts)
    min_c = min(p[1] for p in pts)
    return tuple(sorted((p[0] - min_r, p[1] - min_c) for p in pts))


def orientations(shape: Iterable[Iterable[int]], allow_rotations: bool = True) -> list[Shape]:
    """Distinct orientations (rotations and reflections) of a shape."""
    base = _normalize_shape(shape)
    if not allow_rotations:
        return [base]
    seen: set[Shape] = set()
    out: list[Shape] = []
    current = base
    for _ in range(4):
        for variant in (current, _normalize_shape((r, -c) for r, c in current)):
            if variant not in seen:
                seen.add(variant)
                out.append(variant)
        current = _normalize_shape((c, -r) for r, c in current)
    return out


def shape_sizes(structure: dict) -> list[int]:
    return [len(_normalize_shape(s)) for s in structure["tiles"]]


def placements(structure: dict) -> list[tuple[int, frozenset[Cell]]]:
    """All legal placements as ``(shape_index, covered_cells)``.

    A placement is legal when every covered cell is a remaining cell.
    """
    present = set(cells(structure))
    out: list[tuple[int, frozenset[Cell]]] = []
    seen: set[tuple[int, frozenset[Cell]]] = set()
    for shape_idx, shape in enumerate(structure["tiles"]):
        for orient in orientations(shape, structure.get("allow_rotations", True)):
            for r, c in sorted(present):
                covered = frozenset((r + dr, c + dc) for dr, dc in orient)
                if covered <= present:
                    key = (shape_idx, covered)
                    if key not in seen:
                        seen.add(key)
                        out.append(key)
    return out


def adjacency_edges(structure: dict) -> list[tuple[Cell, Cell]]:
    """Edges between edge-adjacent remaining cells (the domino placement graph)."""
    present = set(cells(structure))
    edges = []
    for r, c in sorted(present):
        for dr, dc in ((0, 1), (1, 0)):
            nb = (r + dr, c + dc)
            if nb in present:
                edges.append(((r, c), nb))
    return edges


def checkerboard_weight(cell: Cell) -> int:
    return 1 if (cell[0] + cell[1]) % 2 == 0 else -1


def color_imbalance(structure: dict) -> int:
    """(# cells with r+c even) - (# cells with r+c odd)."""
    return sum(checkerboard_weight(cell) for cell in cells(structure))


def perfect_matching(structure: dict) -> list[tuple[Cell, Cell]] | None:
    """Exact domino-tilability check via bipartite augmenting paths.

    Returns a list of dominoes covering every cell, or ``None`` if none exists.
    Runs in O(V * E); fine for boards with a few thousand cells.
    """
    present = cells(structure)
    present_set = set(present)
    left = [cell for cell in present if (cell[0] + cell[1]) % 2 == 0]
    right = [cell for cell in present if (cell[0] + cell[1]) % 2 == 1]
    if len(left) != len(right):
        return None
    neighbours = {
        cell: [
            nb
            for nb in ((cell[0] + 1, cell[1]), (cell[0] - 1, cell[1]), (cell[0], cell[1] + 1), (cell[0], cell[1] - 1))
            if nb in present_set
        ]
        for cell in left
    }
    match_right: dict[Cell, Cell] = {}

    def try_augment(u: Cell, visited: set[Cell]) -> bool:
        for v in neighbours[u]:
            if v in visited:
                continue
            visited.add(v)
            if v not in match_right or try_augment(match_right[v], visited):
                match_right[v] = u
                return True
        return False

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, 10 * len(present) + 1000))
    try:
        for u in left:
            if not try_augment(u, set()):
                return None
    finally:
        sys.setrecursionlimit(old_limit)
    return sorted((u, v) for v, u in match_right.items())


def ascii_board(structure: dict, removed_char: str = "X", cell_char: str = ".") -> str:
    removed = removed_cells(structure)
    lines = []
    for r in range(1, structure["rows"] + 1):
        lines.append(" ".join(removed_char if (r, c) in removed else cell_char for c in range(1, structure["cols"] + 1)))
    return "\n".join(lines)
