"""Certificate vocabulary.

A certificate is a plain JSON object with a ``certificate_type`` key. The
per-type schemas live next to their verifiers (``verifiers/<type>.py``
docstrings) and are rendered for models by ``ProblemFamily.certificate_schema_text``.
This module only fixes the vocabulary so that families, verifiers and analysis
agree on names; ``verifiers.available_certificate_types()`` lists the subset
that is actually implemented.
"""
from __future__ import annotations

# Idea-level certificate types (count towards I = 1 when valid).
IDEA_CERTIFICATE_TYPES = (
    "coloring_invariant",
    "modular_invariant",
    "parity_invariant",
    "permutation_parity",
    "gcd_invariant",
    "xor_invariant",
    "potential_function",
    "monovariant",
    "conservation_law",
    "symbolic_identity",
    "explicit_bijection",
    "representation_map",
    "graph_bipartition",
)

# Witness-level certificate types (establish an answer without a reusable idea).
WITNESS_CERTIFICATE_TYPES = ("explicit_construction",)

NONE_CERTIFICATE = "none"


def is_idea_type(certificate_type: str) -> bool:
    return certificate_type in IDEA_CERTIFICATE_TYPES
