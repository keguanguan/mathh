"""Process one raw run directory into tidy tables, metric tables and figures."""
from __future__ import annotations

import csv
from pathlib import Path

from ..utils.serialization import dump_json, load_json, read_jsonl
from .figures import make_all_figures
from .metrics import compute_all
from .tidy import tidy_rows, write_csv


def write_table_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in columns})


def process_run(run_dir: str | Path, processed_root: str | Path = "data/processed", results_root: str | Path = "data/results", n_boot: int = 1000, figures: bool = True) -> dict:
    run_dir = Path(run_dir)
    manifest = load_json(run_dir / "manifest.json")
    records = list(read_jsonl(run_dir / "trials.jsonl"))
    rows = tidy_rows(records)
    rel = Path(manifest["experiment_id"]) / manifest["run_id"]
    processed_dir = Path(processed_root) / rel
    results_dir = Path(results_root) / rel
    write_csv(rows, processed_dir / "tidy.csv")
    tables = compute_all(rows, n_boot=n_boot)
    for name, table in tables.items():
        write_table_csv(table, results_dir / "metrics" / f"{name}.csv")
    summary = {
        "experiment_id": manifest["experiment_id"],
        "run_id": manifest["run_id"],
        "n_trials": len(rows),
        "n_instances": len({r["instance_id"] for r in rows}),
        "models": sorted({r["model"] for r in rows}),
        "families": sorted({r["family"] for r in rows}),
        "I_n_pooled": tables["I_n_pooled"],
        "S_n_pooled": tables["S_n_pooled"],
        "F_pooled": tables["F_pooled"],
        "outcome_counts": tables["outcome_counts"],
        "source_manifest": {k: manifest.get(k) for k in ("code_commit", "code_version", "created")},
    }
    dump_json(summary, results_dir / "summary.json")
    made = make_all_figures(tables, results_dir / "figures") if figures else []
    return {"processed_dir": processed_dir, "results_dir": results_dir, "n_trials": len(rows), "figures": made, "tables": tables}
