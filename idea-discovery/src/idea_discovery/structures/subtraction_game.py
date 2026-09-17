"""Impartial heap game structure (Nim and bounded-subtraction variants).

structure = {
    "kind": "subtraction_game",
    "heaps": [7, 12, 5],
    "max_take": 3,          # remove 1..max_take counters from one heap; null = any number (Nim)
}

Normal play: the player who removes the last counter wins. The state space is
the box prod(h_i + 1), and every move decreases one coordinate, so retrograde
analysis over the box is exact and terminates. ``p_positions`` computes the
losing (P-) positions by dynamic programming; ``theorem_is_p_position`` is the
closed form XOR_i (h_i mod (max_take + 1)) == 0 (Bouton; Sprague-Grundy).
"""
from __future__ import annotations

from functools import reduce
from itertools import product
from typing import Iterable, Optional, Sequence

State = tuple[int, ...]


def make_structure(heaps: Sequence[int], max_take: Optional[int]) -> dict:
    return {"kind": "subtraction_game", "heaps": [int(h) for h in heaps], "max_take": None if max_take is None else int(max_take)}


def moves(structure: dict, state: State) -> Iterable[State]:
    k = structure["max_take"]
    for i, h in enumerate(state):
        top = h if k is None else min(h, k)
        for take in range(1, top + 1):
            yield state[:i] + (h - take,) + state[i + 1 :]


def n_states(structure: dict) -> int:
    out = 1
    for h in structure["heaps"]:
        out *= h + 1
    return out


def states(structure: dict) -> Iterable[State]:
    return product(*(range(h + 1) for h in structure["heaps"]))


def p_positions(structure: dict, max_states: int = 2_000_000) -> set[State]:
    """Exact set of P-positions (previous player wins) within the box, by DP.

    Iterating states in increasing coordinate-sum order guarantees that every
    successor has already been classified.
    """
    if n_states(structure) > max_states:
        raise ValueError(f"state space {n_states(structure)} exceeds {max_states}")
    p: set[State] = set()
    for s in sorted(states(structure), key=sum):
        if not any(nxt in p for nxt in moves(structure, s)):
            p.add(s)  # no move to a P-position (including the terminal state) -> P
    return p


def theorem_is_p_position(structure: dict, state: Optional[State] = None) -> bool:
    state = tuple(structure["heaps"]) if state is None else state
    k = structure["max_take"]
    vals = [h if k is None else h % (k + 1) for h in state]
    return reduce(lambda a, b: a ^ b, vals, 0) == 0


def first_player_wins(structure: dict) -> bool:
    return not theorem_is_p_position(structure)


def winning_move(structure: dict) -> Optional[State]:
    """A move to a P-position from the initial state (by the theorem), if one exists."""
    start = tuple(structure["heaps"])
    for nxt in moves(structure, start):
        if theorem_is_p_position(structure, nxt):
            return nxt
    return None
