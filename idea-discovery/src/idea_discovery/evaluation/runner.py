"""Experiment runner: config -> instances -> trials -> raw JSONL records.

Output layout (one directory per run):

    <output_dir>/<experiment_id>/<run_id>/
        manifest.json     config, code commit, instance hashes, model descriptions
        instances.jsonl   every instance used (full records)
        trials.jsonl      one raw trial record per line (append-only)
        errors.jsonl      trials that raised (with traceback)

Runs are resumable: existing trial_ids in trials.jsonl are skipped.
"""
from __future__ import annotations

import platform
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Callable, Optional

from .. import __version__
from ..families.base import Instance, ProblemFamily, get_family
from ..generation.instances import GenerationSpec, generate_instance_set
from ..models.base import GenerationConfig, ModelRunner, utc_now
from ..models.registry import build_runner
from ..utils.serialization import append_jsonl, dump_json, read_jsonl, write_jsonl
from .config import ExperimentConfig
from .trial import make_trial_id, run_trial


def git_commit(cwd: Optional[Path] = None) -> Optional[str]:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig, run_id: Optional[str] = None, output_root: Optional[Path] = None, resume: bool = False, log: Callable[[str], None] = print):
        self.config = config
        self.run_id = run_id or utc_now().replace(":", "").replace("+0000", "Z")
        self.output_root = Path(output_root) if output_root else Path(config.output_dir)
        self.run_dir = self.output_root / config.experiment_id / self.run_id
        self.resume = resume
        self.log = log
        self.families: dict[str, ProblemFamily] = {}
        self.runners: dict[str, ModelRunner] = {}

    # -- setup -------------------------------------------------------------
    def build(self) -> tuple[dict[str, list[Instance]], dict[str, ModelRunner]]:
        cfg = self.config
        instances: dict[str, list[Instance]] = {}
        for fid in cfg.families:
            fam = get_family(fid, **cfg.family_parameters.get(fid, {}))
            self.families[fid] = fam
            spec = GenerationSpec(fid, cfg.instance_sizes[fid], cfg.transfer_levels, cfg.instances_per_cell, cfg.base_seed, cfg.family_parameters.get(fid))
            instances[fid] = generate_instance_set(spec, fam)
        for m in cfg.models:
            name = m.get("name") or f"{m['provider']}:{m['model']}"
            self.runners[name] = build_runner(m)
        return instances, self.runners

    def _base_config(self) -> GenerationConfig:
        ms = dict(self.config.model_settings)
        return GenerationConfig(temperature=float(ms.get("temperature", 0.0)), max_output_tokens=int(ms.get("max_output_tokens", 4096)), seed=ms.get("seed"), tools_enabled=bool(ms.get("tools_enabled", False)), extra=dict(ms.get("extra", {})))

    def write_manifest(self, instances: dict[str, list[Instance]]) -> None:
        manifest = {
            "experiment_id": self.config.experiment_id,
            "run_id": self.run_id,
            "created": utc_now(),
            "code_version": __version__,
            "code_commit": git_commit(Path(__file__).resolve().parents[3]),
            "python": sys.version,
            "platform": platform.platform(),
            "config": self.config.to_dict(),
            "families": {fid: fam.metadata() for fid, fam in self.families.items()},
            "models": {name: r.describe() for name, r in self.runners.items()},
            "instances": {fid: [{"instance_id": i.instance_id, "content_hash": i.content_hash(), "size": i.size, "transfer_level": i.transfer_level, "answer": i.ground_truth["answer"], "idea_bearing": i.idea_bearing} for i in insts] for fid, insts in instances.items()},
            "n_trials_planned": self.n_trials(instances),
        }
        dump_json(manifest, self.run_dir / "manifest.json")
        write_jsonl((i.to_dict() for insts in instances.values() for i in insts), self.run_dir / "instances.jsonl")

    def n_trials(self, instances: dict[str, list[Instance]]) -> int:
        n_inst = sum(len(v) for v in instances.values())
        return n_inst * len(self.runners) * len(self.config.compute_conditions) * self.config.repetitions

    # -- execution -----------------------------------------------------------
    def run(self) -> Path:
        instances, runners = self.build()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        trials_path = self.run_dir / "trials.jsonl"
        done: set[str] = set()
        if self.resume and trials_path.exists():
            done = {rec["trial_id"] for rec in read_jsonl(trials_path)}
            self.log(f"resuming: {len(done)} trials already recorded")
        elif trials_path.exists():
            raise FileExistsError(f"{trials_path} exists; use resume=True or a new run_id")
        self.write_manifest(instances)
        base_config = self._base_config()
        total = self.n_trials(instances)
        count = 0
        n_errors = 0
        for fid, insts in instances.items():
            fam = self.families[fid]
            for inst in insts:
                for name, runner in runners.items():
                    for compute in self.config.compute_conditions:
                        for rep in range(self.config.repetitions):
                            count += 1
                            trial_id = make_trial_id(self.config.experiment_id, name, compute.name, inst.instance_id, rep)
                            if trial_id in done:
                                continue
                            try:
                                record = run_trial(
                                    fam, inst, runner, base_config, compute, self.config.conditions, rep,
                                    experiment_id=self.config.experiment_id, model_name=name, render_format=self.config.render_format,
                                    extra_metadata={"run_id": self.run_id, "code_version": __version__},
                                )
                            except Exception as e:  # noqa: BLE001 - log and continue; never lose completed trials
                                n_errors += 1
                                append_jsonl({"trial_id": trial_id, "error": repr(e), "traceback": traceback.format_exc(), "timestamp": utc_now()}, self.run_dir / "errors.jsonl")
                                self.log(f"[{count}/{total}] ERROR {trial_id}: {e!r}")
                                continue
                            append_jsonl(record, trials_path)
                            done.add(trial_id)
                            if count % 10 == 0 or count == total:
                                self.log(f"[{count}/{total}] {trial_id}")
        self.log(f"run complete: {len(done)} trials written to {trials_path} ({n_errors} errors)")
        return self.run_dir
