"""Problem families. Importing this package registers all built-in families."""
from . import difference_board, domino_tiling, population_game, sliding_puzzle, subtraction_game  # noqa: F401  (registration)
from .base import (
    TRANSFER_LEVELS,
    CanonicalIdea,
    ExtractedCertificate,
    Instance,
    ProblemFamily,
    available_families,
    get_family,
    register_family,
)

__all__ = [
    "TRANSFER_LEVELS", "CanonicalIdea", "ExtractedCertificate", "Instance", "ProblemFamily",
    "available_families", "get_family", "register_family",
]
