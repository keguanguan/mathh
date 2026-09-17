#!/usr/bin/env python
"""Process a raw run into tidy tables, metric tables (I(n), S(n), I(d), S(d), I(c), S(c), F) and figures.

    python scripts/process_results.py --run data/raw_runs/mock_scaling_v0/<run_id>
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.analysis.process import process_run


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="raw run directory (contains trials.jsonl)")
    ap.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    ap.add_argument("--results-root", type=Path, default=Path("data/results"))
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--reextract", action="store_true", help="re-run free-response extraction with the current extractors (raw trials untouched)")
    args = ap.parse_args()
    out = process_run(args.run, args.processed_root, args.results_root, n_boot=args.n_boot, figures=not args.no_figures, reextract=args.reextract)
    print(f"tidy table : {out['processed_dir'] / 'tidy.csv'} ({out['n_trials']} trials)")
    print(f"metrics    : {out['results_dir'] / 'metrics'}")
    for fig in out["figures"]:
        print(f"figure     : {fig}")
    for name, label in (("I_n_pooled", "I(n)"), ("S_n_pooled", "S(n)"), ("F_pooled", "F")):
        print(f"{label} pooled:")
        for row in out["tables"][name]:
            key = f"n={row['size']:4d}" if "size" in row else ""
            print(f"  {row['model']:24s} {key:8s} p={row['p']:.2f}  wilson [{row['ci_low']:.2f}, {row['ci_high']:.2f}]  (k={row['k']}/{row['n']})")


if __name__ == "__main__":
    main()
