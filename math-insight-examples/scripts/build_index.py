#!/usr/bin/env python3
"""Build data/index.jsonl: one JSON object per problem entry.

The index is a flat, machine-friendly view of the YAML entries.  It contains
the identifying metadata plus the key idea, but not the long prose fields, so
it stays small and diff-friendly.  Run this after adding or editing entries:

    python scripts/build_index.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INDEX_PATH, REPO_ROOT, load_all_entries, load_taxonomy  # noqa: E402


def _iso(value):
    return value.isoformat() if isinstance(value, date) else value


def index_record(entry: dict, taxonomy: dict) -> dict:
    cat = entry["key_idea"]["category"]
    tax = taxonomy.get(cat, {})
    src = entry.get("source", {})
    return {
        "id": entry["id"],
        "title": entry["title"],
        "path": entry["_path"].relative_to(REPO_ROOT).as_posix(),
        "folder": entry["_folder"],
        "domain": entry["problem"].get("domain"),
        "answer": entry["problem"].get("answer"),
        "key_idea": entry["key_idea"]["name"],
        "category": cat,
        "root_category": tax.get("root", cat),
        "key_idea_summary": " ".join(entry["key_idea"]["summary"].split()),
        "source_name": src.get("name"),
        "source_url": src.get("url"),
        "source_accessed": _iso(src.get("accessed")),
        "additional_sources": [s.get("name") for s in (entry.get("additional_sources") or [])],
        "tags": entry.get("tags", []),
        "aliases": entry.get("aliases", []),
        "quality": entry.get("quality", {}),
        "familiarity": entry.get("familiarity", {}),
    }


def main() -> int:
    taxonomy = load_taxonomy()
    entries = load_all_entries()
    with INDEX_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for entry in entries:
            fh.write(json.dumps(index_record(entry, taxonomy), ensure_ascii=False) + "\n")
    print(f"Wrote {len(entries)} records to {INDEX_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
