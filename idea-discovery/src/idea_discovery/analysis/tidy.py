"""Raw trial records -> one tidy row per trial.

The tidy table is the interface to later statistical modelling (e.g.
mixed-effects logistic regressions with family and instance effects). It
contains only observable outcomes; nothing is aggregated here.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Optional

TIDY_COLUMNS = [
    "trial_id", "experiment_id", "run_id",
    "model", "provider", "model_id",
    "family", "instance_id", "instance_hash", "size", "transfer_level", "compute_level", "compute_rank", "repetition",
    "idea_bearing", "ground_truth_answer", "answer_parsed", "solution_correct",
    "idea_present", "idea_valid", "idea_canonical", "idea_structural_valid", "witness_valid",
    "verification_method", "verification_exact", "extraction_method",
    "posthoc_valid", "posthoc_stated_none", "posthoc_canonical",
    "formalization_valid", "formalization_canonical",
    "recognized_classic",
    "outcome_category",
]


def outcome_category(solution_correct: Optional[bool], idea_valid: bool, witness_valid: bool) -> str:
    if solution_correct is None:
        return "unparsed_answer"
    if idea_valid:
        return "idea_correct" if solution_correct else "idea_incorrect"
    if solution_correct:
        return "correct_with_witness" if witness_valid else "correct_unclassified"
    return "incorrect_no_idea"


def trial_to_row(rec: dict) -> dict:
    inst = rec["instance"]
    model = rec["model"]
    fs = rec.get("free_solve") or {}
    ex = rec.get("idea_extraction") or {}
    ver = rec.get("verification") or {}
    ph = rec.get("posthoc_formalization") or {}
    sb = rec.get("supplied_idea_baseline") or {}
    rc = rec.get("retrieval_control") or {}
    compute = model.get("compute_condition") or {}
    solution_correct = fs.get("answer_correct") if fs else None
    idea_valid = bool(ex.get("idea_valid", False))
    witness_valid = bool(ex.get("witness_valid", False))
    return {
        "trial_id": rec["trial_id"],
        "experiment_id": rec["trial_id"].split("__")[0],
        "run_id": (rec.get("metadata") or {}).get("run_id"),
        "model": model.get("model_name"),
        "provider": model.get("provider"),
        "model_id": model.get("model"),
        "family": inst["family_id"],
        "instance_id": inst["instance_id"],
        "instance_hash": inst.get("content_hash"),
        "size": inst["size"],
        "transfer_level": inst["transfer_level"],
        "compute_level": compute.get("name", "default"),
        "compute_rank": compute.get("rank"),
        "repetition": rec.get("repetition", 0),
        "idea_bearing": bool(inst.get("idea_bearing")),
        "ground_truth_answer": inst.get("ground_truth_answer"),
        "answer_parsed": (fs.get("parsed_answer") or {}).get("parsed") if fs else None,
        "solution_correct": solution_correct,
        "idea_present": bool(ex.get("idea_present", False)),
        "idea_valid": idea_valid,
        "idea_canonical": ex.get("canonical_match"),
        "idea_structural_valid": ver.get("structural_valid"),
        "witness_valid": witness_valid,
        "verification_method": ver.get("method"),
        "verification_exact": ver.get("exact"),
        "extraction_method": ex.get("extraction_method"),
        "posthoc_valid": ph.get("valid") if ph else None,
        "posthoc_stated_none": ph.get("stated_none") if ph else None,
        "posthoc_canonical": ph.get("canonical_match") if ph else None,
        "formalization_valid": sb.get("valid") if sb else None,
        "formalization_canonical": sb.get("canonical_match") if sb else None,
        "recognized_classic": rc.get("recognized") if rc else None,
        "outcome_category": outcome_category(solution_correct, idea_valid, witness_valid) if fs else "no_free_solve",
    }


def tidy_rows(records: Iterable[dict]) -> list[dict]:
    return [trial_to_row(r) for r in records]


def _to_cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    return v


def write_csv(rows: list[dict], path: str | Path, columns: list[str] = TIDY_COLUMNS) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _to_cell(r.get(k)) for k in columns})


_BOOL_COLS = {"idea_bearing", "solution_correct", "idea_present", "idea_valid", "idea_canonical", "idea_structural_valid", "witness_valid", "verification_exact", "posthoc_valid", "posthoc_stated_none", "posthoc_canonical", "formalization_valid", "formalization_canonical", "recognized_classic"}
_INT_COLS = {"size", "transfer_level", "compute_rank", "repetition"}


def read_csv(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out = {}
            for k, v in r.items():
                if v == "":
                    out[k] = None
                elif k in _BOOL_COLS:
                    out[k] = v == "1"
                elif k in _INT_COLS:
                    out[k] = int(v)
                else:
                    out[k] = v
            rows.append(out)
    return rows
