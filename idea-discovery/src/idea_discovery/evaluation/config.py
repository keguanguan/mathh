"""Experiment configuration loading and validation.

An experiment config (configs/experiments/*.yaml) fully determines a run:

    experiment_id: mock_scaling_v0
    families: [domino_tiling, population_game]
    family_parameters: {domino_tiling: {possible_fraction: 0.35}}
    models: [mock_size_dependent]            # names under configs/models/ or inline dicts
    instance_sizes: {domino_tiling: [6, 8], population_game: [12, 24]}
    transfer_levels: [1]
    compute_conditions: [default]            # names under configs/compute_conditions.yaml or inline dicts
    repetitions: 1
    instances_per_cell: 4
    generation_seeds: {base_seed: 1234}
    conditions: {free_solve: true, posthoc: true, supplied_idea: true, recognition: true}
    model_settings: {temperature: 0.0, max_output_tokens: 4096}
    render_format: text
    output_dir: data/raw_runs
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..families.base import available_families
from ..models.base import ComputeCondition
from ..utils.serialization import load_yaml

DEFAULT_CONDITIONS = {"free_solve": True, "posthoc": True, "supplied_idea": True, "recognition": True}


class ConfigError(ValueError):
    pass


@dataclass
class ExperimentConfig:
    experiment_id: str
    families: list[str]
    models: list[dict]
    instance_sizes: dict[str, list[int]]
    transfer_levels: list[int]
    compute_conditions: list[ComputeCondition]
    repetitions: int = 1
    instances_per_cell: int = 4
    base_seed: int = 0
    conditions: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_CONDITIONS))
    model_settings: dict = field(default_factory=dict)
    family_parameters: dict[str, dict] = field(default_factory=dict)
    render_format: str = "text"
    output_dir: str = "data/raw_runs"
    description: str = ""
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = dict(self.raw)
        d["_resolved"] = {
            "models": self.models,
            "compute_conditions": [c.to_dict() for c in self.compute_conditions],
            "conditions": self.conditions,
            "base_seed": self.base_seed,
        }
        return d


def _resolve_named(entry: Any, directory: Optional[Path], kind: str) -> dict:
    if isinstance(entry, dict):
        return entry
    if not isinstance(entry, str):
        raise ConfigError(f"{kind} entries must be names or dicts, got {entry!r}")
    if directory is None:
        raise ConfigError(f"cannot resolve {kind} {entry!r} without a configs directory")
    path = directory / f"{entry}.yaml"
    if not path.exists():
        raise ConfigError(f"{kind} config {path} not found")
    data = load_yaml(path)
    data.setdefault("name", entry)
    return data


def _resolve_compute(entry: Any, table: dict) -> ComputeCondition:
    if isinstance(entry, dict):
        return ComputeCondition(entry["name"], entry.get("provider_parameters", {}), entry.get("rank"))
    if entry not in table:
        raise ConfigError(f"compute condition {entry!r} not defined; known: {sorted(table)}")
    spec = table[entry]
    return ComputeCondition(entry, spec.get("provider_parameters", {}), spec.get("rank"))


def load_experiment_config(path: str | Path, configs_root: Optional[str | Path] = None) -> ExperimentConfig:
    path = Path(path)
    raw = load_yaml(path)
    if configs_root is None:
        configs_root = path.parent.parent if path.parent.name == "experiments" else path.parent
    configs_root = Path(configs_root)
    return build_experiment_config(raw, configs_root)


def build_experiment_config(raw: dict, configs_root: Optional[Path] = None) -> ExperimentConfig:
    for key in ("experiment_id", "families", "models", "instance_sizes", "transfer_levels", "compute_conditions"):
        if key not in raw:
            raise ConfigError(f"experiment config missing required key {key!r}")
    families = list(raw["families"])
    unknown = [f for f in families if f not in available_families()]
    if unknown:
        raise ConfigError(f"unknown families {unknown}; available: {available_families()}")
    sizes_raw = raw["instance_sizes"]
    if isinstance(sizes_raw, list):
        instance_sizes = {f: [int(s) for s in sizes_raw] for f in families}
    else:
        instance_sizes = {f: [int(s) for s in sizes_raw[f]] for f in families if f in sizes_raw}
        missing = [f for f in families if f not in instance_sizes]
        if missing:
            raise ConfigError(f"instance_sizes missing for families {missing}")
    models_dir = configs_root / "models" if configs_root else None
    models = [_resolve_named(m, models_dir, "model") for m in raw["models"]]
    for m in models:
        for key in ("provider", "model"):
            if key not in m:
                raise ConfigError(f"model config {m.get('name', m)} missing {key!r}")
    compute_table = {}
    if configs_root and (configs_root / "compute_conditions.yaml").exists():
        compute_table = load_yaml(configs_root / "compute_conditions.yaml") or {}
    compute_conditions = [_resolve_compute(c, compute_table) for c in raw["compute_conditions"]]
    names = [c.name for c in compute_conditions]
    if len(set(names)) != len(names):
        raise ConfigError("duplicate compute condition names")
    transfer_levels = [int(t) for t in raw["transfer_levels"]]
    seeds = raw.get("generation_seeds") or {}
    conditions = dict(DEFAULT_CONDITIONS)
    conditions.update(raw.get("conditions") or {})
    if conditions.get("posthoc") and not conditions.get("free_solve"):
        raise ConfigError("posthoc condition requires free_solve")
    return ExperimentConfig(
        experiment_id=str(raw["experiment_id"]),
        families=families,
        models=models,
        instance_sizes=instance_sizes,
        transfer_levels=transfer_levels,
        compute_conditions=compute_conditions,
        repetitions=int(raw.get("repetitions", 1)),
        instances_per_cell=int(raw.get("instances_per_cell", 4)),
        base_seed=int(seeds.get("base_seed", 0)),
        conditions=conditions,
        model_settings=dict(raw.get("model_settings") or {}),
        family_parameters=dict(raw.get("family_parameters") or {}),
        render_format=str(raw.get("render_format", "text")),
        output_dir=str(raw.get("output_dir", "data/raw_runs")),
        description=str(raw.get("description", "")),
        raw=raw,
    )
