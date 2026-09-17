"""Sliding-puzzle structure: tokens on the vertices of a graph, one vertex empty.

structure = {
    "kind": "sliding_puzzle",
    "rows": R, "cols": C,                 # grid presentation (vertices = cells, edges = adjacency)
    "start": [[...], ...],                # R x C, 0 = blank
    "target": [[...], ...],
}

Cells are 1-based (row, col); the *reading order* is row-major. A move slides
a tile that is edge-adjacent to the blank into the blank cell.

Parity invariants (verified against the move rule, never by search):
    phi = (inversions of the chosen sequence + w(blank cell)) mod 2
where the sequence is either all cells in reading order with the blank read
as the largest value ("all_cells") or the tiles only ("tiles_only"), and w is
a 0/1 weight on cells. For a move along the edge (u, v):
    all_cells   : one transposition                -> inversion parity flips
    tiles_only  : the tile jumps |pos(u)-pos(v)|-1 tiles -> parity changes by that
so phi is invariant iff for every edge  delta_perm(u, v) + w(u) + w(v) == 0 (mod 2).

Ground truth: for rectangular boards with at least two rows and two columns the
parity condition is exact (Wilson 1974; Johnson-Story 1879 for 4 x 4) - the
reachable set is exactly the parity class of the start. ``bfs_reachable`` is
provided to confirm this exhaustively on small boards in tests.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Iterable, Sequence

Cell = tuple[int, int]
Grid = tuple[tuple[int, ...], ...]


def make_structure(rows: int, cols: int, start: Sequence[Sequence[int]], target: Sequence[Sequence[int]]) -> dict:
    return {"kind": "sliding_puzzle", "rows": int(rows), "cols": int(cols), "start": [list(map(int, r)) for r in start], "target": [list(map(int, r)) for r in target]}


def to_grid(rows_: Sequence[Sequence[int]]) -> Grid:
    return tuple(tuple(int(x) for x in r) for r in rows_)


def cells(structure: dict) -> list[Cell]:
    return [(r, c) for r in range(1, structure["rows"] + 1) for c in range(1, structure["cols"] + 1)]


def reading_index(structure: dict) -> dict[Cell, int]:
    return {cell: i for i, cell in enumerate(cells(structure))}


def edges(structure: dict) -> list[tuple[Cell, Cell]]:
    R, C = structure["rows"], structure["cols"]
    out = []
    for r in range(1, R + 1):
        for c in range(1, C + 1):
            if c < C:
                out.append(((r, c), (r, c + 1)))
            if r < R:
                out.append(((r, c), (r + 1, c)))
    return out


def blank_position(grid: Grid) -> Cell:
    for r, row in enumerate(grid, start=1):
        for c, v in enumerate(row, start=1):
            if v == 0:
                return (r, c)
    raise ValueError("grid has no blank (0)")


def neighbours(structure: dict, cell: Cell) -> list[Cell]:
    R, C = structure["rows"], structure["cols"]
    r, c = cell
    return [(r + dr, c + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 1 <= r + dr <= R and 1 <= c + dc <= C]


def slide(grid: Grid, tile_cell: Cell) -> Grid:
    """Slide the tile at ``tile_cell`` into the blank (must be adjacent)."""
    b = blank_position(grid)
    if abs(b[0] - tile_cell[0]) + abs(b[1] - tile_cell[1]) != 1:
        raise ValueError(f"{tile_cell} is not adjacent to the blank {b}")
    rows_ = [list(r) for r in grid]
    rows_[b[0] - 1][b[1] - 1] = rows_[tile_cell[0] - 1][tile_cell[1] - 1]
    rows_[tile_cell[0] - 1][tile_cell[1] - 1] = 0
    return to_grid(rows_)


def successors(structure: dict, grid: Grid) -> list[tuple[int, Grid]]:
    """(tile value moved, resulting grid) for every legal move."""
    b = blank_position(grid)
    out = []
    for nb in neighbours(structure, b):
        out.append((grid[nb[0] - 1][nb[1] - 1], slide(grid, nb)))
    return out


def inversion_parity(seq: Sequence[int]) -> int:
    inv = 0
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            if seq[i] > seq[j]:
                inv += 1
    return inv % 2


def sequence(structure: dict, grid: Grid, permutation_of: str) -> list[int]:
    n_cells = structure["rows"] * structure["cols"]
    flat = [grid[r - 1][c - 1] for r, c in cells(structure)]
    if permutation_of == "all_cells":
        return [n_cells if v == 0 else v for v in flat]
    if permutation_of == "tiles_only":
        return [v for v in flat if v != 0]
    raise ValueError(f"unknown permutation_of {permutation_of!r}")


def parity_invariant(structure: dict, grid: Grid, permutation_of: str, blank_weight: dict[Cell, int]) -> int:
    return (inversion_parity(sequence(structure, grid, permutation_of)) + blank_weight[blank_position(grid)]) % 2


def delta_perm(structure: dict, u: Cell, v: Cell, permutation_of: str) -> int:
    """Change of inversion parity when the blank and a tile swap along edge (u, v)."""
    if permutation_of == "all_cells":
        return 1
    idx = reading_index(structure)
    return (abs(idx[u] - idx[v]) - 1) % 2


def canonical_weight(structure: dict) -> dict[Cell, int]:
    return {(r, c): (r + c) % 2 for r, c in cells(structure)}


def canonical_invariant(structure: dict, grid: Grid) -> int:
    return parity_invariant(structure, grid, "all_cells", canonical_weight(structure))


def parity_reachable(structure: dict) -> bool:
    """Exact answer for rectangular boards (rows, cols >= 2): same parity class."""
    if structure["rows"] < 2 or structure["cols"] < 2:
        raise ValueError("parity ground truth requires at least 2 rows and 2 columns")
    s, t = to_grid(structure["start"]), to_grid(structure["target"])
    return canonical_invariant(structure, s) == canonical_invariant(structure, t)


def random_walk(structure: dict, grid: Grid, steps: int, rng: random.Random) -> tuple[Grid, list[int]]:
    """Random legal moves without immediate backtracking; returns (grid, moved tiles)."""
    moves: list[int] = []
    last_blank = None
    for _ in range(steps):
        b = blank_position(grid)
        options = [nb for nb in neighbours(structure, b) if nb != last_blank]
        nb = rng.choice(options)
        moves.append(grid[nb[0] - 1][nb[1] - 1])
        grid = slide(grid, nb)
        last_blank = b
    return grid, moves


def apply_tile_moves(structure: dict, grid: Grid, tiles: Iterable[int]) -> Grid:
    """Apply moves given as the tile values slid; raises if a move is illegal."""
    for t in tiles:
        b = blank_position(grid)
        candidates = [nb for nb in neighbours(structure, b) if grid[nb[0] - 1][nb[1] - 1] == t]
        if not candidates:
            raise ValueError(f"tile {t} is not adjacent to the blank at {b}")
        grid = slide(grid, candidates[0])
    return grid


def bfs_reachable(structure: dict, max_states: int = 400_000) -> bool:
    """Exhaustive reachability (small boards only; used to validate the parity rule)."""
    start, target = to_grid(structure["start"]), to_grid(structure["target"])
    seen = {start}
    queue = deque([start])
    while queue:
        g = queue.popleft()
        if g == target:
            return True
        for _, nxt in successors(structure, g):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
                if len(seen) > max_states:
                    raise ValueError("state space too large for BFS")
    return False
