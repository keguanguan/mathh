"""Shared helpers for the repository scripts.

Everything here is deliberately dependency-light: only PyYAML is required.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PROBLEMS_DIR = DATA_DIR / "problems"
TAXONOMY_PATH = DATA_DIR / "taxonomy.yaml"
INDEX_PATH = DATA_DIR / "index.jsonl"


def load_taxonomy() -> dict[str, dict]:
    """Return a flat map ``category_id -> info``.

    ``info`` has keys ``name``, ``folder``, ``parent`` (``None`` for roots),
    ``root`` (the id of the top-level ancestor) and ``description``.
    """
    with TAXONOMY_PATH.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    flat: dict[str, dict] = {}

    def walk(node: dict, parent: str | None, root: str) -> None:
        cid = node["id"]
        if cid in flat:
            raise ValueError(f"duplicate taxonomy id: {cid}")
        flat[cid] = {
            "name": node.get("name", cid),
            "folder": node["folder"],
            "parent": parent,
            "root": root,
            "description": (node.get("description") or "").strip(),
        }
        for child in node.get("children", []) or []:
            walk(child, cid, root)

    for top in raw["categories"]:
        walk(top, None, top["id"])
    return flat


def iter_entry_paths() -> Iterator[Path]:
    """Yield every problem file, sorted for reproducible output."""
    yield from sorted(PROBLEMS_DIR.glob("*/*.yaml"))


def load_entry(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        entry = yaml.safe_load(fh)
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    entry["_path"] = path
    entry["_folder"] = path.parent.name
    return entry


def load_all_entries() -> list[dict]:
    return [load_entry(p) for p in iter_entry_paths()]


_WS = re.compile(r"\s+")
_NONWORD = re.compile(r"[^a-z0-9 ]+")


def normalize_text(text: str) -> str:
    """Lower-case, strip punctuation and collapse whitespace."""
    text = (text or "").lower()
    text = _NONWORD.sub(" ", text)
    return _WS.sub(" ", text).strip()


STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "in", "on", "to", "is", "it", "that",
    "this", "with", "for", "by", "be", "are", "as", "at", "from", "into", "can",
    "one", "two", "each", "any", "all", "no", "not", "if", "so", "we", "you",
    "there", "which", "its", "their", "than", "then", "some", "such", "only",
    "every", "same", "other", "more", "prove", "show", "possible", "problem",
}


def word_set(text: str) -> set[str]:
    return {w for w in normalize_text(text).split() if w not in STOPWORDS and len(w) > 2}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
