"""Abstract mathematical structures.

A family's :class:`Instance` carries a ``structure`` dict with a ``kind`` key.
Verifiers operate on structures, not on families, so that instances from
different families (or different surface presentations of the same family)
sharing a structure can be verified by the same code.

Supported kinds:
    ``tiling``       - a set of cells and a list of tile shapes (see tiling.py)
    ``vector_game``       - integer count vectors with a finite set of move vectors
    ``sliding_puzzle``    - tokens on grid cells with one blank; slide into the blank
    ``subtraction_game``  - heaps of counters; remove 1..k from one heap; normal play
    ``difference_board``  - set of integers closed under writing differences
"""
from . import difference_board, sliding_puzzle, subtraction_game, tiling, vector_game

__all__ = ["difference_board", "sliding_puzzle", "subtraction_game", "tiling", "vector_game"]
