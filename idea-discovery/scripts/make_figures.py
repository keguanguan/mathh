#!/usr/bin/env python
"""Regenerate figures from a processed tidy table (without touching raw records).

    python scripts/make_figures.py --tidy data/processed/<exp>/<run_id>/tidy.csv --out data/results/<exp>/<run_id>/figures
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.analysis import compute_all, make_all_figures, read_csv


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tidy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args()
    rows = read_csv(args.tidy)
    tables = compute_all(rows, n_boot=args.n_boot)
    for fig in make_all_figures(tables, args.out):
        print(f"figure: {fig}")


if __name__ == "__main__":
    main()
