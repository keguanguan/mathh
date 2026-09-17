"""Vector game structure: integer count vectors under a finite set of move vectors.

structure = {
    "kind": "vector_game",
    "classes": ["A", "B", "C"],
    "moves": [[-1, -1, 2], [-1, 2, -1], [2, -1, -1]],
    "initial": [13, 15, 17],
    "targets": [[45, 0, 0], [0, 45, 0], [0, 0, 45]],
    "target_description": "all objects of a single class",
}

A move ``v`` is applicable in state ``s`` when ``s + v`` is component-wise
non-negative. The population sum is conserved when every move sums to 0,
which bounds the reachable state space and makes exhaustive ground truth
(BFS) exact for moderate totals.
"""
from __future__ import annotations

from collections import deque
from itertools import combinations, product
from math import comb
from typing import Iterable, Sequence

State = tuple[int, ...]


def make_structure(
    classes: Sequence[str],
    moves: Iterable[Sequence[int]],
    initial: Sequence[int],
    targets: Iterable[Sequence[int]],
    target_description: str,
) -> dict:
    return {
        "kind": "vector_game",
        "classes": list(classes),
        "moves": [list(map(int, m)) for m in moves],
        "initial": list(map(int, initial)),
        "targets": [list(map(int, t)) for t in targets],
        "target_description": target_description,
    }


def dimension(structure: dict) -> int:
    return len(structure["classes"])


def total(structure: dict) -> int:
    return sum(structure["initial"])


def is_conservative(structure: dict) -> bool:
    return all(sum(m) == 0 for m in structure["moves"])


def apply_move(state: State, move: Sequence[int]) -> State | None:
    new = tuple(s + m for s, m in zip(state, move))
    if any(x < 0 for x in new):
        return None
    return new


def single_class_targets(k: int, n: int) -> list[list[int]]:
    return [[n if j == i else 0 for j in range(k)] for i in range(k)]


def count_states(k: int, n: int) -> int:
    """Number of non-negative integer k-vectors with sum n."""
    return comb(n + k - 1, k - 1)


def enumerate_states(k: int, n: int) -> Iterable[State]:
    """All non-negative integer k-vectors with sum n (compositions)."""
    for bars in combinations(range(n + k - 1), k - 1):
        prev = -1
        out = []
        for b in bars:
            out.append(b - prev - 1)
            prev = b
        out.append(n + k - 1 - prev - 1)
        yield tuple(out)


def reachability(structure: dict, max_states: int = 2_000_000) -> tuple[bool, list[int] | None, int]:
    """Exact BFS from the initial state.

    Returns ``(reachable, move_index_path_or_None, n_states_explored)``.
    Raises ``ValueError`` if the game is not conservative (state space unbounded).
    """
    if not is_conservative(structure):
        raise ValueError("BFS ground truth requires conservative moves (each move sums to 0)")
    start: State = tuple(structure["initial"])
    targets = {tuple(t) for t in structure["targets"]}
    moves = structure["moves"]
    parent: dict[State, tuple[State, int] | None] = {start: None}
    queue: deque[State] = deque([start])
    while queue:
        state = queue.popleft()
        if state in targets:
            path: list[int] = []
            cur = state
            while parent[cur] is not None:
                prev, idx = parent[cur]
                path.append(idx)
                cur = prev
            return True, path[::-1], len(parent)
        for idx, move in enumerate(moves):
            nxt = apply_move(state, move)
            if nxt is not None and nxt not in parent:
                parent[nxt] = (state, idx)
                queue.append(nxt)
                if len(parent) > max_states:
                    raise ValueError(f"state space exceeds {max_states} states")
    return False, None, len(parent)


def linear_form(coefficients: Sequence[int], state: Sequence[int], modulus: int) -> int:
    return sum(int(a) * int(s) for a, s in zip(coefficients, state)) % modulus


def kernel_vectors_mod(moves: Sequence[Sequence[int]], modulus: int, k: int) -> list[tuple[int, ...]]:
    """All non-zero coefficient vectors alpha (mod m) with alpha . v == 0 (mod m) for every move."""
    out = []
    for alpha in product(range(modulus), repeat=k):
        if all(a == 0 for a in alpha):
            continue
        if all(linear_form(alpha, m, modulus) == 0 for m in moves):
            out.append(alpha)
    return out
