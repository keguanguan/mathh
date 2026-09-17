#!/usr/bin/env python3
"""Validate every problem entry against the schema in docs/DATA_FORMAT.md
and run duplicate detection.

Usage:
    python scripts/validate_entries.py            # validate + duplicate report
    python scripts/validate_entries.py --strict   # warnings also fail
    python scripts/validate_entries.py --no-dups  # skip duplicate detection

Exit status is 1 if any error (or, with --strict, any warning) is found.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    PROBLEMS_DIR,
    jaccard,
    load_all_entries,
    load_taxonomy,
    normalize_text,
    word_set,
)

ID_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
URL_RE = re.compile(r"^https?://\S+$")
QUALITY_LEVELS = {"low", "medium", "high"}
QUALITY_KEYS = ["clarity_of_key_idea", "elegance", "naive_search_contrast", "pedagogical_value"]

# (dotted path, required?)  -- every leaf must be a non-empty string unless noted
REQUIRED_STRINGS = [
    "title",
    "source.name",
    "source.url",
    "source.accessed",
    "problem.statement",
    "problem.domain",
    "problem.answer",
    "key_idea.name",
    "key_idea.category",
    "key_idea.summary",
    "intuitive_proof.explanation",
    "reasoning_structure.naive_approach",
    "reasoning_structure.crucial_observation",
    "reasoning_structure.why_it_simplifies",
]
OPTIONAL_STRINGS = ["source.original_title", "source.author", "source.notes", "notes"]

# Thresholds for duplicate detection
TITLE_MATCH = 1.0        # exact normalized title/alias match
STATEMENT_JACCARD = 0.45  # word-set similarity of problem statements
IDEA_JACCARD = 0.60       # word-set similarity of key-idea summaries
SHARED_URL_MIN_JACCARD = 0.30  # a shared URL counts only with this much statement overlap
COLLECTION_URL_THRESHOLD = 3   # URLs cited by more entries than this are treated as collections
MIN_STATEMENT_WORDS = 8        # very short statements give unreliable similarity scores


def get(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"{path.relative_to(PROBLEMS_DIR.parent.parent)}: {msg}")

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append(f"{path.relative_to(PROBLEMS_DIR.parent.parent)}: {msg}")


def validate_entry(entry: dict, taxonomy: dict, rep: Report) -> None:
    path: Path = entry["_path"]

    # --- id / filename -----------------------------------------------------
    eid = entry.get("id")
    if not isinstance(eid, str) or not ID_RE.match(eid):
        rep.error(path, f"id must be snake_case, got {eid!r}")
    elif eid != path.stem:
        rep.error(path, f"id {eid!r} does not match filename {path.stem!r}")

    # --- required / optional strings ----------------------------------------
    for key in REQUIRED_STRINGS:
        val = get(entry, key)
        if key == "source.accessed" and isinstance(val, date):
            continue  # PyYAML parses ISO dates into date objects
        if not isinstance(val, str) or not val.strip():
            rep.error(path, f"missing or empty required field {key}")
    for key in OPTIONAL_STRINGS:
        val = get(entry, key)
        if val is not None and not isinstance(val, str):
            rep.error(path, f"field {key} must be a string if present")

    # --- source -------------------------------------------------------------
    url = get(entry, "source.url")
    if isinstance(url, str) and not URL_RE.match(url):
        rep.error(path, f"source.url is not a URL: {url}")
    accessed = get(entry, "source.accessed")
    if accessed is not None:
        if isinstance(accessed, date):
            pass  # YAML parsed an ISO date
        elif not (isinstance(accessed, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", accessed)):
            rep.error(path, f"source.accessed must be YYYY-MM-DD, got {accessed!r}")
    for i, extra in enumerate(entry.get("additional_sources") or []):
        if not isinstance(extra, dict) or not extra.get("name"):
            rep.error(path, f"additional_sources[{i}] must be a mapping with a name")
        elif extra.get("url") and not URL_RE.match(str(extra["url"])):
            rep.error(path, f"additional_sources[{i}].url is not a URL")

    # --- taxonomy / folder ----------------------------------------------------
    cat = get(entry, "key_idea.category")
    if cat not in taxonomy:
        rep.error(path, f"key_idea.category {cat!r} is not in data/taxonomy.yaml")
    else:
        expected = taxonomy[cat]["folder"]
        if entry["_folder"] != expected:
            rep.error(path, f"category {cat!r} belongs in folder {expected!r}, file is in {entry['_folder']!r}")

    # --- lists ---------------------------------------------------------------
    for key in ("tags", "aliases", "related"):
        val = entry.get(key)
        if val is None:
            if key == "tags":
                rep.error(path, "tags list is required")
            continue
        if not isinstance(val, list) or not all(isinstance(x, str) and x.strip() for x in val):
            rep.error(path, f"{key} must be a list of non-empty strings")
        elif len(set(val)) != len(val):
            rep.warn(path, f"{key} contains duplicates")
    if isinstance(entry.get("tags"), list) and len(entry["tags"]) < 2:
        rep.warn(path, "fewer than two tags")

    # --- quality / familiarity -----------------------------------------------
    quality = entry.get("quality")
    if not isinstance(quality, dict):
        rep.error(path, "quality block is required")
    else:
        for key in QUALITY_KEYS:
            if quality.get(key) not in QUALITY_LEVELS:
                rep.error(path, f"quality.{key} must be one of {sorted(QUALITY_LEVELS)}")
    fam = entry.get("familiarity")
    if not isinstance(fam, dict):
        rep.error(path, "familiarity block is required")
    else:
        for key in ("famous", "likely_widely_known"):
            if not isinstance(fam.get(key), bool):
                rep.error(path, f"familiarity.{key} must be a boolean")

    # --- soft quality checks ---------------------------------------------------
    stmt = get(entry, "problem.statement") or ""
    if isinstance(stmt, str) and len(stmt.split()) > 220:
        rep.warn(path, "problem.statement is long (>220 words); keep statements concise")
    expl = get(entry, "intuitive_proof.explanation") or ""
    if isinstance(expl, str) and len(expl.split()) > 400:
        rep.warn(path, "intuitive_proof.explanation is long (>400 words)")
    summary = get(entry, "key_idea.summary") or ""
    if isinstance(summary, str) and len(summary.split()) > 80:
        rep.warn(path, "key_idea.summary should be a couple of sentences (>80 words)")


def find_duplicates(entries: list[dict]) -> list[tuple[str, str, str]]:
    """Return a list of (id_a, id_b, reason) for suspicious pairs.

    Signals used:
      * identical normalized title, or a title matching another entry's alias;
      * a shared source URL (main or additional) together with a mild
        overlap between the statements (books are cited by many entries);
      * high word-overlap between problem statements;
      * high word-overlap between key-idea summaries combined with a moderate
        overlap between statements.
    Pairs that declare each other in ``related`` are skipped.
    """
    info = []
    for e in entries:
        names = {normalize_text(e.get("title", ""))}
        names |= {normalize_text(a) for a in (e.get("aliases") or [])}
        names.discard("")
        urls = {str(get(e, "source.url") or "").rstrip("/")}
        urls |= {str(s.get("url", "")).rstrip("/") for s in (e.get("additional_sources") or [])}
        urls.discard("")
        info.append({
            "id": e.get("id", e["_path"].stem),
            "related": set(e.get("related") or []),
            "names": names,
            "urls": urls,
            "stmt": word_set(get(e, "problem.statement") or ""),
            "idea": word_set(get(e, "key_idea.summary") or ""),
        })

    # URLs cited by many entries are books or collection pages, not evidence
    # of duplication; ignore them.
    url_count: dict[str, int] = {}
    for rec in info:
        for u in rec["urls"]:
            url_count[u] = url_count.get(u, 0) + 1
    for rec in info:
        rec["urls"] = {u for u in rec["urls"] if url_count[u] <= COLLECTION_URL_THRESHOLD}

    hits = []
    for a, b in combinations(info, 2):
        if b["id"] in a["related"] or a["id"] in b["related"]:
            continue  # declared as distinct-but-related; not a duplicate
        reasons = []
        js = jaccard(a["stmt"], b["stmt"])
        ji = jaccard(a["idea"], b["idea"])
        if a["names"] & b["names"]:
            reasons.append(f"shared title/alias {sorted(a['names'] & b['names'])[0]!r}")
        # A shared URL alone is weak evidence (books and collection pages are
        # cited by many entries); require some overlap in the statements too.
        if a["urls"] & b["urls"] and js >= SHARED_URL_MIN_JACCARD:
            reasons.append(f"shared source URL {sorted(a['urls'] & b['urls'])[0]} (statement similarity {js:.2f})")
        if js >= STATEMENT_JACCARD and min(len(a["stmt"]), len(b["stmt"])) >= MIN_STATEMENT_WORDS:
            reasons.append(f"statement similarity {js:.2f}")
        if ji >= IDEA_JACCARD and js >= STATEMENT_JACCARD / 2:
            reasons.append(f"key-idea similarity {ji:.2f}")
        if reasons:
            hits.append((a["id"], b["id"], "; ".join(reasons)))
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--no-dups", action="store_true", help="skip duplicate detection")
    args = ap.parse_args(argv)

    taxonomy = load_taxonomy()
    rep = Report()
    entries = []
    for path in sorted(PROBLEMS_DIR.glob("*/*.yaml")):
        try:
            from common import load_entry
            entries.append(load_entry(path))
        except Exception as exc:  # noqa: BLE001
            rep.error(path, f"cannot parse YAML: {exc}")

    seen_ids: dict[str, Path] = {}
    for e in entries:
        validate_entry(e, taxonomy, rep)
        eid = e.get("id")
        if isinstance(eid, str):
            if eid in seen_ids:
                rep.error(e["_path"], f"duplicate id {eid!r} (also in {seen_ids[eid].name})")
            seen_ids[eid] = e["_path"]
    for e in entries:
        for rid in e.get("related") or []:
            if rid not in seen_ids:
                rep.error(e["_path"], f"related id {rid!r} does not exist")
            elif rid == e.get("id"):
                rep.warn(e["_path"], "entry lists itself as related")

    dups = [] if args.no_dups else find_duplicates(entries)

    print(f"Checked {len(entries)} entries in {PROBLEMS_DIR.relative_to(PROBLEMS_DIR.parent.parent)}")
    for line in rep.errors:
        print("ERROR  ", line)
    for line in rep.warnings:
        print("WARN   ", line)
    if dups:
        print("\nPossible duplicates (review manually; merge or add aliases):")
        for a, b, why in dups:
            print(f"  {a}  <->  {b}: {why}")
    else:
        if not args.no_dups:
            print("No duplicate candidates found.")

    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s), {len(dups)} duplicate candidate(s)")
    failed = bool(rep.errors) or (args.strict and (rep.warnings or dups))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
