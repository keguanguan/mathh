"""Difference-board structure (Euclid's game): a set of positive integers that
grows by writing differences.

structure = {
    "kind": "difference_board",
    "numbers": [36, 60, 84],
    "target": 18,
    "operation": "abs_difference",   # write |a - b| for two numbers a, b on the board, if new
}

Question: can ``target`` ever be written? With g = gcd(numbers) and M = max,
every number written is a positive multiple of g not exceeding M, and every
such multiple is eventually written whatever the play (the final board is
forced). So target is reachable iff g | target and 0 < target <= M
(``exact_reachable``); ``closure`` computes the forced final board and
``witness_moves`` a concrete sequence producing the target.
"""
from __future__ import annotations

from math import gcd
from functools import reduce
from typing import Optional, Sequence

OPERATIONS = ("abs_difference",)


def make_structure(numbers: Sequence[int], target: int, operation: str = "abs_difference") -> dict:
    if operation not in OPERATIONS:
        raise ValueError(f"unknown operation {operation!r}")
    return {"kind": "difference_board", "numbers": sorted(int(x) for x in numbers), "target": int(target), "operation": operation}


def board_gcd(numbers: Sequence[int]) -> int:
    return reduce(gcd, numbers, 0)


def apply(operation: str, a: int, b: int) -> int:
    if operation == "abs_difference":
        return abs(a - b)
    raise ValueError(operation)


def preserves_divisibility(operation: str, d: int) -> bool:
    """Exact check that the operation maps multiples of d to multiples of d
    (residue classes suffice since the operation is compatible with congruence)."""
    if d <= 0:
        return False
    for a in range(0, d):
        for b in range(0, d):
            if a % d == 0 and b % d == 0:
                # |a - b| for representatives a, b and for a + d, b (both signs of the difference)
                if apply(operation, a, b) % d != 0 or apply(operation, a + d, b) % d != 0 or apply(operation, a, b + d) % d != 0:
                    return False
    return True


def closure(structure: dict, max_size: int = 20_000) -> set[int]:
    """All numbers that can ever appear (positive results only)."""
    board = set(structure["numbers"])
    frontier = list(board)
    while frontier:
        x = frontier.pop()
        for y in list(board):
            z = apply(structure["operation"], x, y)
            if z > 0 and z not in board:
                board.add(z)
                frontier.append(z)
                if len(board) > max_size:
                    raise ValueError("closure too large")
    return board


def exact_reachable(structure: dict) -> bool:
    g = board_gcd(structure["numbers"])
    t = structure["target"]
    if t in structure["numbers"]:
        return True
    return t > 0 and t % g == 0 and t <= max(structure["numbers"])


def witness_moves(structure: dict) -> Optional[list[list[int]]]:
    """A sequence of (a, b) pairs whose differences, written in order, produce the target.

    Greedy Euclid-style play: repeatedly write the smallest missing multiple of
    g as a difference of two present numbers; terminates because the final
    board is forced.
    """
    t = structure["target"]
    board = set(structure["numbers"])
    if t in board:
        return []
    if not exact_reachable(structure):
        return None
    op = structure["operation"]
    moves: list[list[int]] = []
    while t not in board:
        progressed = False
        for a in sorted(board):
            for b in sorted(board):
                if a > b:
                    z = apply(op, a, b)
                    if z > 0 and z not in board:
                        board.add(z)
                        moves.append([a, b])
                        progressed = True
                        break
            if progressed:
                break
        if not progressed:
            return None  # pragma: no cover - contradicts exact_reachable
    return moves
