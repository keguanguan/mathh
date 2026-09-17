#!/usr/bin/env python3
"""Regenerate docs/TAXONOMY.md from data/taxonomy.yaml and the entry counts.

    python scripts/build_docs.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO_ROOT, TAXONOMY_PATH, load_all_entries  # noqa: E402

OUT_PATH = REPO_ROOT / "docs" / "TAXONOMY.md"

INTRO = """# Taxonomy of key ideas

The taxonomy lives in `data/taxonomy.yaml`; this page is a readable rendering of it
(regenerate with `python scripts/build_docs.py`). Every entry has exactly one main idea,
`key_idea.category`, which must be one of the ids below; additional ideas go in `tags`.
The `folder` column is where entries with that main idea are stored under `data/problems/`.

A problem is *not* filed under `invariant` just because an invariant appears somewhere in
the proof: the category names the observation that makes the problem collapse. When several
ideas cooperate (e.g. a parity invariant plus an induction), the category is the one a reader
would name first, and the others are tags.
"""


def main() -> int:
    raw = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8"))
    entries = load_all_entries()
    counts = Counter(e["key_idea"]["category"] for e in entries)
    ids_by_cat: dict[str, list[str]] = defaultdict(list)
    for e in entries:
        ids_by_cat[e["key_idea"]["category"]].append(e["id"])

    lines = [INTRO, "| id | name | folder | entries |", "|---|---|---|---:|"]

    def row(node: dict, depth: int) -> None:
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
        lines.append(f"| `{node['id']}` | {indent}{node['name']} | `{node['folder']}` | {counts.get(node['id'], 0)} |")
        for child in node.get("children", []) or []:
            row(child, depth + 1)

    for top in raw["categories"]:
        row(top, 0)

    lines += ["", "## Descriptions and examples", ""]

    def desc(node: dict, depth: int) -> None:
        cid = node["id"]
        lines.append(f"{'###' if depth == 0 else '####'} `{cid}` — {node['name']}")
        lines.append("")
        lines.append(" ".join((node.get("description") or "").split()))
        if ids_by_cat.get(cid):
            lines.append("")
            lines.append("Entries: " + ", ".join(f"`{i}`" for i in sorted(ids_by_cat[cid])))
        lines.append("")
        for child in node.get("children", []) or []:
            desc(child, depth + 1)

    for top in raw["categories"]:
        desc(top, 0)

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
