"""Stable hashing and seed derivation (reproducibility helpers)."""
from __future__ import annotations

import hashlib
from typing import Any

from .serialization import canonical_json


def stable_hash(obj: Any, length: int = 16) -> str:
    """Hex digest of the canonical JSON encoding of ``obj``."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:length]


def derive_seed(*parts: Any) -> int:
    """Deterministically derive a 63-bit integer seed from arbitrary parts."""
    digest = hashlib.sha256(canonical_json(list(parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
