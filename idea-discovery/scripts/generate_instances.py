#!/usr/bin/env python
"""Generate (and sanity-check) a deterministic instance set for a family.

    python scripts/generate_instances.py --family domino_tiling --sizes 6 8 12 \
        --levels 1 2 --per-cell 4 --base-seed 1234 --out data/generated/domino_tiling.jsonl
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.families import available_families, get_family
from idea_discovery.generation import GenerationSpec, generate_instance_set
from idea_discovery.utils.serialization import write_jsonl


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", required=True, choices=available_families())
    ap.add_argument("--sizes", type=int, nargs="+", required=True)
    ap.add_argument("--levels", type=int, nargs="+", default=[1])
    ap.add_argument("--per-cell", type=int, default=4)
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--show", action="store_true", help="print the rendered problem of each instance")
    args = ap.parse_args()
    fam = get_family(args.family)
    spec = GenerationSpec(args.family, args.sizes, args.levels, args.per_cell, args.base_seed)
    instances = generate_instance_set(spec, fam)
    out = args.out or Path("data/generated") / f"{args.family}_seed{args.base_seed}.jsonl"
    write_jsonl((i.to_dict() for i in instances), out)
    answers = {}
    for inst in instances:
        answers[inst.ground_truth["answer"]] = answers.get(inst.ground_truth["answer"], 0) + 1
        if args.show:
            print(f"=== {inst.instance_id} [{inst.ground_truth['answer']}, idea_bearing={inst.idea_bearing}]")
            print(fam.render_problem(inst))
            print()
    print(f"wrote {len(instances)} instances to {out}; answers: {answers}; all sanity checks passed")


if __name__ == "__main__":
    main()
