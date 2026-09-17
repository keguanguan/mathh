"""Access to the curated seed-problem corpus (math-insight-examples).

The corpus is maintained in a separate repository; this module only *reads*
it. Families reference a seed by id and use its problem statement for the
classical (d0) presentation when the corpus is available, falling back to an
embedded statement otherwise. Nothing in the primary experiments depends on
the corpus being present.

Location: ``$IDEA_SEED_CORPUS`` (a ``data/problems`` directory), else
``../math-insight-examples/data/problems`` relative to this repository.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ..utils.serialization import load_yaml


def corpus_dir() -> Optional[Path]:
    env = os.environ.get("IDEA_SEED_CORPUS")
    candidates = [Path(env)] if env else []
    candidates.append(Path(__file__).resolve().parents[3].parent / "math-insight-examples" / "data" / "problems")
    for c in candidates:
        if c.is_dir():
            return c
    return None


@lru_cache(maxsize=None)
def load_seed(seed_id: str) -> Optional[dict]:
    """The corpus entry with this id (any category folder), or None."""
    root = corpus_dir()
    if root is None:
        return None
    for path in root.glob(f"*/{seed_id}.yaml"):
        data = load_yaml(path)
        if isinstance(data, dict):
            data["_path"] = str(path)
            return data
    return None


def seed_statement(seed_id: str) -> Optional[str]:
    seed = load_seed(seed_id)
    if not seed:
        return None
    return (seed.get("problem") or {}).get("statement", "").strip() or None


def seed_provenance(seed_id: str) -> dict:
    seed = load_seed(seed_id)
    if not seed:
        return {"seed_id": seed_id, "corpus": None}
    src = seed.get("source") or {}
    return {"seed_id": seed_id, "corpus": "math-insight-examples", "title": seed.get("title"), "source_name": src.get("name"), "source_url": src.get("url"), "key_idea_category": (seed.get("key_idea") or {}).get("category")}
