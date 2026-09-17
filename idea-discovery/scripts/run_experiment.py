#!/usr/bin/env python
"""Run an experiment from a config.

    python scripts/run_experiment.py --config configs/experiments/mock_scaling_v0.yaml
"""
import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.evaluation import ExperimentRunner, load_experiment_config


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--run-id", default=None, help="run identifier (default: UTC timestamp)")
    ap.add_argument("--output-root", type=Path, default=None, help="override output_dir from the config")
    ap.add_argument("--resume", action="store_true", help="skip trials already present in trials.jsonl")
    ap.add_argument("--dry-run", action="store_true", help="build instances and runners, print the plan, do not call models")
    args = ap.parse_args()
    config = load_experiment_config(args.config)
    runner = ExperimentRunner(config, run_id=args.run_id, output_root=args.output_root, resume=args.resume)
    if args.dry_run:
        instances, runners = runner.build()
        for fid, insts in instances.items():
            print(f"{fid}: {len(insts)} instances; sizes {sorted({i.size for i in insts})}; levels {sorted({i.transfer_level for i in insts})}")
        print(f"models: {list(runners)}; compute: {[c.name for c in config.compute_conditions]}; repetitions: {config.repetitions}")
        print(f"planned trials: {runner.n_trials(instances)} -> {runner.run_dir}")
        return
    run_dir = runner.run()
    print(f"run directory: {run_dir}")


if __name__ == "__main__":
    main()
